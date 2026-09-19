"""リマインダー/通知(F-09)。詳細設計書4.10章。

通知は都度、元データから算出する(通知本体は保存しない)。確認済みの状態のみ
notification_acknowledgementsに保存する。
"""
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Protocol

from app.core.constants import HOME_NOTIFICATION_LIMIT, NOTIFICATION_LEAD_DAYS
from app.enums import NotificationSourceType, PaymentStatus
from app.exceptions import NotFoundError
from app.repositories.deadline_repository import DeadlineRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.notification_ack_repository import NotificationAckRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.quote_repository import QuoteRepository
from app.services.deadline_service import DeadlineService
from app.services.payment_service import PaymentService
from app.utils.due_state import DueState, judge_due_state

logger = logging.getLogger("app")

RESOLVED_MESSAGE = "対象の通知は既に解消されています"
SOURCE_MISSING_MESSAGE = "通知の元データが見つかりません"
TYPE_ORDER = {t.value: i for i, t in enumerate(NotificationSourceType)}
DEADLINE_CATEGORY_LABELS = {"TAX_FILING": "確定申告", "CONTRACT_RENEWAL": "契約更新", "OTHER": "その他"}


@dataclass
class NotificationCandidate:
    source_type: str
    source_id: int
    title: str
    due_date: date
    state: DueState
    days_diff: int
    link: str
    category: str | None = None


@dataclass
class NotificationItem:
    candidate: NotificationCandidate
    acknowledged: bool = False


@dataclass
class NotificationListResult:
    items: list[NotificationItem]
    errors: list[str] = field(default_factory=list)


@dataclass
class NotificationSummaryResult:
    unacknowledged_count: int
    overdue_count: int
    items: list[NotificationItem]
    errors: list[str] = field(default_factory=list)


class NotificationSourceProvider(Protocol):
    source_type: str

    def collect(self, today: date) -> list[NotificationCandidate]: ...

    def source_exists(self, source_id: int) -> bool: ...


def _limit_date(today: date) -> str:
    return (today + timedelta(days=NOTIFICATION_LEAD_DAYS)).isoformat()


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        logger.warning("Skipping notification source with invalid date: %r", value)
        return None


def _candidate(
    source_type: str, source_id: int, title: str, due_text: str, today: date, link: str, category: str | None = None
) -> NotificationCandidate | None:
    due = _parse_date(due_text)
    if due is None:
        return None
    state = judge_due_state(due, today)
    if state is None:
        return None
    return NotificationCandidate(source_type, source_id, title, due, state, (due - today).days, link, category)


class InvoiceDueProvider:
    source_type = NotificationSourceType.INVOICE_DUE.value

    def __init__(self, invoice_repository: InvoiceRepository, payment_service: PaymentService):
        self.invoice_repository = invoice_repository
        self.payment_service = payment_service

    def collect(self, today: date) -> list[NotificationCandidate]:
        result = []
        for invoice in self.invoice_repository.list_due_before(_limit_date(today)):
            if self.payment_service.calculate_status(invoice) == PaymentStatus.PAID:
                continue
            client_name = invoice.client.name if invoice.client else ""
            cand = _candidate(
                self.source_type, invoice.id, f"請求書 {invoice.invoice_number}({client_name})の支払期限",
                invoice.due_date, today, f"/invoices/{invoice.id}",
            )
            if cand:
                result.append(cand)
        return result

    def source_exists(self, source_id: int) -> bool:
        return self.invoice_repository.find_by_id(source_id) is not None


class QuoteExpiryProvider:
    source_type = NotificationSourceType.QUOTE_EXPIRY.value

    def __init__(self, quote_repository: QuoteRepository):
        self.quote_repository = quote_repository

    def collect(self, today: date) -> list[NotificationCandidate]:
        result = []
        for quote in self.quote_repository.list_expiring_before(_limit_date(today)):
            client_name = quote.client.name if quote.client else ""
            cand = _candidate(
                self.source_type, quote.id, f"見積書 {quote.quote_number}({client_name})の有効期限",
                quote.expiry_date, today, f"/quotes/{quote.id}",
            )
            if cand:
                result.append(cand)
        return result

    def source_exists(self, source_id: int) -> bool:
        return self.quote_repository.find_by_id(source_id) is not None


class ProjectDueProvider:
    source_type = NotificationSourceType.PROJECT_DUE.value

    def __init__(self, project_repository: ProjectRepository):
        self.project_repository = project_repository

    def collect(self, today: date) -> list[NotificationCandidate]:
        result = []
        for project in self.project_repository.list_due_before(_limit_date(today)):
            cand = _candidate(
                self.source_type, project.id, f"案件「{project.name}」の納期", project.due_date, today,
                f"/projects/{project.id}",
            )
            if cand:
                result.append(cand)
        return result

    def source_exists(self, source_id: int) -> bool:
        return self.project_repository.find_by_id(source_id) is not None


class DeadlineProvider:
    source_type = NotificationSourceType.DEADLINE.value

    def __init__(self, deadline_repository: DeadlineRepository):
        self.deadline_repository = deadline_repository

    def collect(self, today: date) -> list[NotificationCandidate]:
        result = []
        for deadline in self.deadline_repository.list_due_before(_limit_date(today)):
            label = DEADLINE_CATEGORY_LABELS.get(deadline.category, deadline.category)
            title = deadline.name if deadline.name == label else f"{deadline.name}({label})"
            cand = _candidate(
                self.source_type, deadline.id, title, deadline.due_date, today,
                "/deadlines", deadline.category,
            )
            if cand:
                result.append(cand)
        return result

    def source_exists(self, source_id: int) -> bool:
        return self.deadline_repository.find_by_id(source_id) is not None


def _is_hidden(ack, cand: NotificationCandidate) -> bool:
    """確認済みとして非表示にするか(詳細設計書4.10.4)。"""
    if ack is None:
        return False
    if ack.acknowledged_due_date != cand.due_date.isoformat():
        return False  # 期限日が変更された(新しい期限として扱う)
    if ack.acknowledged_state == "UPCOMING" and cand.state == "OVERDUE":
        return False  # 状態が進んだ(近い→超過)
    return True


def _sort_key(cand: NotificationCandidate):
    return (0 if cand.state == "OVERDUE" else 1, cand.due_date, TYPE_ORDER[cand.source_type], cand.source_id)


class NotificationService:
    def __init__(
        self,
        providers: list[NotificationSourceProvider],
        ack_repository: NotificationAckRepository,
        deadline_repository: DeadlineRepository,
        deadline_service: DeadlineService,
    ):
        self.providers = providers
        self.ack_repository = ack_repository
        self.deadline_repository = deadline_repository
        self.deadline_service = deadline_service

    def _collect_all(self, today: date) -> tuple[list[NotificationItem], list[str]]:
        """種類ごとに個別にtry/exceptで取得し、失敗した種類はerrorsへ(他の種類は継続。4.10.6)。"""
        items: list[NotificationItem] = []
        errors: list[str] = []
        for provider in self.providers:
            try:
                candidates = provider.collect(today)
            except Exception:  # noqa: BLE001 - 種類単位で握りつぶすのが仕様
                logger.exception("Notification provider %s failed", provider.source_type)
                errors.append(provider.source_type)
                continue
            # 取得できた種類のみ、解消済みの確認済み記録を整理する
            self.ack_repository.delete_not_in(provider.source_type, {c.source_id for c in candidates})
            acks = {a.source_id: a for a in self.ack_repository.list_by_type(provider.source_type)}
            for cand in candidates:
                items.append(NotificationItem(cand, _is_hidden(acks.get(cand.source_id), cand)))
        items.sort(key=lambda i: _sort_key(i.candidate))
        return items, errors

    def list_notifications(self, include_acknowledged: bool = False, today: date | None = None) -> NotificationListResult:
        items, errors = self._collect_all(today or date.today())
        if not include_acknowledged:
            items = [i for i in items if not i.acknowledged]
        return NotificationListResult(items, errors)

    def get_summary(self, limit: int = HOME_NOTIFICATION_LIMIT, today: date | None = None) -> NotificationSummaryResult:
        items, errors = self._collect_all(today or date.today())
        visible = [i for i in items if not i.acknowledged]
        return NotificationSummaryResult(
            unacknowledged_count=len(visible),
            overdue_count=sum(1 for i in visible if i.candidate.state == "OVERDUE"),
            items=visible[:limit],
            errors=errors,
        )

    def _find_candidate(self, source_type: str, source_id: int, today: date) -> NotificationCandidate:
        provider = next((p for p in self.providers if p.source_type == source_type), None)
        if provider is None:
            raise NotFoundError(SOURCE_MISSING_MESSAGE)
        try:
            candidates = provider.collect(today)
        except Exception as exc:  # noqa: BLE001 - 取得失敗は未処理の500にせず404へ変換する
            logger.exception("Notification provider %s failed on acknowledge", source_type)
            raise NotFoundError(SOURCE_MISSING_MESSAGE) from exc
        for cand in candidates:
            if cand.source_id == source_id:
                return cand
        try:
            exists = provider.source_exists(source_id)
        except Exception as exc:  # noqa: BLE001 - collectと同様、未処理の500にせず404へ変換する
            logger.exception("Notification provider %s failed on source existence check", source_type)
            raise NotFoundError(SOURCE_MISSING_MESSAGE) from exc
        if exists:
            raise NotFoundError(RESOLVED_MESSAGE)
        # 通知元が削除済み: 残っている確認済み記録を整理する。get_dbは例外時にロールバックするため、
        # 404を返す前に明示的にコミットして削除を確定させる
        self.ack_repository.delete(source_type, source_id)
        self.ack_repository.session.commit()
        raise NotFoundError(SOURCE_MISSING_MESSAGE)

    def acknowledge(self, source_type: str, source_id: int, today: date | None = None) -> None:
        today = today or date.today()
        source_type = str(source_type)
        cand = self._find_candidate(source_type, source_id, today)  # 状態・期限日はサーバー算出値を正とする
        if source_type == NotificationSourceType.DEADLINE.value and cand.state == "OVERDUE":
            deadline = self.deadline_repository.find_by_id(source_id)
            if deadline is not None and deadline.is_recurring:
                self.deadline_service.roll_forward(deadline, today)
                self.ack_repository.delete(source_type, source_id)
                return
        self.ack_repository.upsert(
            source_type, source_id, cand.state, cand.due_date.isoformat(),
            datetime.now().isoformat(timespec="seconds"),
        )

    def unacknowledge(self, source_type: str, source_id: int) -> None:
        self.ack_repository.delete(str(source_type), source_id)
