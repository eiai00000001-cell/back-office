"""通知(F-09)。詳細設計書4.10章。提供クラス・NotificationServiceのテスト。"""
from datetime import date, timedelta

import pytest

from app.exceptions import NotFoundError
from app.models.client import Client
from app.models.expense import Expense  # noqa: F401
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.project import Project
from app.models.quote import Quote
from app.models.reminder_deadline import ReminderDeadline
from app.repositories.deadline_repository import DeadlineRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.notification_ack_repository import NotificationAckRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.quote_repository import QuoteRepository
from app.services.deadline_service import DeadlineService
from app.services.notification_service import (
    DeadlineProvider,
    InvoiceDueProvider,
    NotificationCandidate,
    NotificationService,
    ProjectDueProvider,
    QuoteExpiryProvider,
    _is_hidden,
)
from app.services.payment_service import PaymentService
from tests.conftest import now_iso

TODAY = date(2026, 9, 19)


def d(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


@pytest.fixture()
def client_row(db_session):
    c = Client(name="サンプル商事", created_at=now_iso(), updated_at=now_iso())
    db_session.add(c)
    db_session.commit()
    return c


def make_invoice(db_session, client, number, due, total=10000, paid=0, project_id=None):
    inv = Invoice(
        invoice_number=number, client_id=client.id, issue_date="2026-08-01", due_date=due,
        subtotal_amount=total, tax_amount=0, total_amount=total, project_id=project_id,
        created_at=now_iso(), updated_at=now_iso(),
    )
    db_session.add(inv)
    db_session.flush()
    if paid:
        db_session.add(Payment(invoice_id=inv.id, payment_date="2026-09-01", amount=paid, created_at=now_iso()))
    db_session.commit()
    return inv


def make_quote(db_session, client, number, expiry, status="CONFIRMED"):
    q = Quote(
        quote_number=number, client_id=client.id, issue_date="2026-08-01", expiry_date=expiry, status=status,
        subtotal_amount=100, tax_amount=0, total_amount=100, created_at=now_iso(), updated_at=now_iso(),
    )
    db_session.add(q)
    db_session.commit()
    return q


def make_project(db_session, name, due, status="IN_PROGRESS"):
    p = Project(name=name, due_date=due, status=status, created_at=now_iso(), updated_at=now_iso())
    db_session.add(p)
    db_session.commit()
    return p


def make_deadline(db_session, name, due, category="OTHER", recurring=0):
    dl = ReminderDeadline(
        name=name, due_date=due, category=category, is_recurring=recurring, created_at=now_iso(), updated_at=now_iso()
    )
    db_session.add(dl)
    db_session.commit()
    return dl


def build_service(db_session, providers=None):
    payment_service = PaymentService(PaymentRepository(db_session))
    ack_repo = NotificationAckRepository(db_session)
    deadline_repo = DeadlineRepository(db_session)
    if providers is None:
        providers = [
            InvoiceDueProvider(InvoiceRepository(db_session), payment_service),
            QuoteExpiryProvider(QuoteRepository(db_session)),
            ProjectDueProvider(ProjectRepository(db_session)),
            DeadlineProvider(deadline_repo),
        ]
    return NotificationService(providers, ack_repo, deadline_repo, DeadlineService(deadline_repo, ack_repo))


class TestInvoiceDueProvider:
    def _collect(self, db_session):
        return InvoiceDueProvider(InvoiceRepository(db_session), PaymentService(PaymentRepository(db_session))).collect(TODAY)

    def test_overdue_and_upcoming_unpaid_and_partial(self, db_session, client_row):
        over = make_invoice(db_session, client_row, "2026-0001", d(-3))
        soon = make_invoice(db_session, client_row, "2026-0002", d(7), paid=100)
        make_invoice(db_session, client_row, "2026-0003", d(8))  # 8日先は対象外
        result = {c.source_id: c for c in self._collect(db_session)}
        assert set(result) == {over.id, soon.id}
        assert result[over.id].state == "OVERDUE"
        assert result[over.id].days_diff == -3
        assert result[soon.id].state == "UPCOMING"
        assert result[soon.id].days_diff == 7
        assert result[over.id].title == "請求書 2026-0001(サンプル商事)の支払期限"
        assert result[over.id].link == f"/invoices/{over.id}"
        assert result[over.id].source_type == "INVOICE_DUE"

    def test_due_today_is_upcoming(self, db_session, client_row):
        make_invoice(db_session, client_row, "2026-0001", d(0))
        assert self._collect(db_session)[0].state == "UPCOMING"

    def test_paid_and_null_due_date_are_excluded(self, db_session, client_row):
        make_invoice(db_session, client_row, "2026-0001", d(-3), paid=10000)
        make_invoice(db_session, client_row, "2026-0002", None)
        assert self._collect(db_session) == []


class TestQuoteExpiryProvider:
    def test_unconverted_quotes_only(self, db_session, client_row):
        draft = make_quote(db_session, client_row, "2026-0001", d(-1), status="DRAFT")
        confirmed = make_quote(db_session, client_row, "2026-0002", d(5))
        converted = make_quote(db_session, client_row, "2026-0003", d(2))
        make_quote(db_session, client_row, "2026-0004", d(30))
        make_quote(db_session, client_row, "2026-0005", None)
        inv = make_invoice(db_session, client_row, "2026-0001", d(60))
        inv.source_quote_id = converted.id
        db_session.commit()
        result = {c.source_id: c for c in QuoteExpiryProvider(QuoteRepository(db_session)).collect(TODAY)}
        assert set(result) == {draft.id, confirmed.id}
        assert result[draft.id].state == "OVERDUE"
        assert result[confirmed.id].title == "見積書 2026-0002(サンプル商事)の有効期限"
        assert result[confirmed.id].link == f"/quotes/{confirmed.id}"


class TestProjectDueProvider:
    def test_excludes_done_and_null_due(self, db_session):
        a = make_project(db_session, "サイト制作", d(-2))
        make_project(db_session, "完了済", d(-2), status="DONE")
        make_project(db_session, "納期なし", None)
        make_project(db_session, "先の案件", d(20))
        result = ProjectDueProvider(ProjectRepository(db_session)).collect(TODAY)
        assert [c.source_id for c in result] == [a.id]
        assert result[0].title == "案件「サイト制作」の納期"
        assert result[0].link == f"/projects/{a.id}"
        assert result[0].state == "OVERDUE"


class TestDeadlineProvider:
    def test_includes_past_and_within_lead_days_with_category(self, db_session):
        past = make_deadline(db_session, "過去の期限", d(-100), category="TAX_FILING")
        soon = make_deadline(db_session, "契約", d(3), category="CONTRACT_RENEWAL")
        make_deadline(db_session, "先", d(30))
        result = {c.source_id: c for c in DeadlineProvider(DeadlineRepository(db_session)).collect(TODAY)}
        assert set(result) == {past.id, soon.id}
        assert result[past.id].state == "OVERDUE"
        assert result[past.id].category == "TAX_FILING"
        assert result[soon.id].title == "契約(契約更新)"
        assert result[soon.id].link == "/deadlines"

    def test_title_omits_kind_when_name_equals_kind_label(self, db_session):
        same = make_deadline(db_session, "確定申告", d(3), category="TAX_FILING")
        other = make_deadline(db_session, "その他", d(4), category="OTHER")
        result = {c.source_id: c for c in DeadlineProvider(DeadlineRepository(db_session)).collect(TODAY)}
        assert result[same.id].title == "確定申告"
        assert result[other.id].title == "その他"

    def test_title_keeps_kind_when_name_differs_from_kind_label(self, db_session):
        dl = make_deadline(db_session, "令和8年分 確定申告", d(3), category="TAX_FILING")
        result = {c.source_id: c for c in DeadlineProvider(DeadlineRepository(db_session)).collect(TODAY)}
        assert result[dl.id].title == "令和8年分 確定申告(確定申告)"


class TestIsHidden:
    def cand(self, state, due=d(3)):
        return NotificationCandidate("INVOICE_DUE", 1, "t", date.fromisoformat(due), state, 3, "/x", None)

    class Ack:
        def __init__(self, state, due):
            self.acknowledged_state = state
            self.acknowledged_due_date = due

    def test_no_ack_visible(self):
        assert _is_hidden(None, self.cand("UPCOMING")) is False

    def test_same_state_and_due_hidden(self):
        assert _is_hidden(self.Ack("UPCOMING", d(3)), self.cand("UPCOMING")) is True

    def test_due_date_changed_reappears(self):
        assert _is_hidden(self.Ack("UPCOMING", d(2)), self.cand("UPCOMING")) is False

    def test_upcoming_to_overdue_reappears(self):
        assert _is_hidden(self.Ack("UPCOMING", d(-1)), self.cand("OVERDUE", d(-1))) is False

    def test_overdue_stays_hidden_until_resolved(self):
        assert _is_hidden(self.Ack("OVERDUE", d(-1)), self.cand("OVERDUE", d(-1))) is True


class TestNotificationServiceList:
    def test_order_overdue_first_then_due_date_then_type(self, db_session, client_row):
        make_project(db_session, "P近", d(2))
        make_deadline(db_session, "D近", d(2))
        make_invoice(db_session, client_row, "2026-0001", d(2))
        make_invoice(db_session, client_row, "2026-0002", d(-10))
        make_project(db_session, "P超過", d(-5))
        result = build_service(db_session).list_notifications(today=TODAY)
        titles = [i.candidate.title for i in result.items]
        assert titles == [
            "請求書 2026-0002(サンプル商事)の支払期限",
            "案件「P超過」の納期",
            "請求書 2026-0001(サンプル商事)の支払期限",
            "案件「P近」の納期",
            "D近(その他)",
        ]
        assert result.errors == []

    def test_acknowledged_hidden_by_default_and_shown_with_flag(self, db_session, client_row):
        inv = make_invoice(db_session, client_row, "2026-0001", d(2))
        make_deadline(db_session, "D", d(2))
        service = build_service(db_session)
        service.acknowledge("INVOICE_DUE", inv.id, today=TODAY)
        assert [i.candidate.source_type for i in service.list_notifications(today=TODAY).items] == ["DEADLINE"]
        with_ack = service.list_notifications(include_acknowledged=True, today=TODAY).items
        assert {(i.candidate.source_type, i.acknowledged) for i in with_ack} == {("INVOICE_DUE", True), ("DEADLINE", False)}

    def test_one_notification_per_source(self, db_session, client_row):
        make_invoice(db_session, client_row, "2026-0001", d(-1), paid=1)
        items = build_service(db_session).list_notifications(today=TODAY).items
        assert len(items) == 1

    def test_provider_failure_is_isolated(self, db_session, client_row):
        class Broken:
            source_type = "QUOTE_EXPIRY"

            def collect(self, today):
                raise RuntimeError("boom")

        make_invoice(db_session, client_row, "2026-0001", d(-1))
        service = build_service(db_session)
        service.providers = [p if p.source_type != "QUOTE_EXPIRY" else Broken() for p in service.providers]
        result = service.list_notifications(today=TODAY)
        assert result.errors == ["QUOTE_EXPIRY"]
        assert len(result.items) == 1

    def test_all_providers_failing_returns_empty_with_four_errors(self, db_session):
        class Broken:
            def __init__(self, t):
                self.source_type = t

            def collect(self, today):
                raise RuntimeError("boom")

        types = ["INVOICE_DUE", "QUOTE_EXPIRY", "PROJECT_DUE", "DEADLINE"]
        service = build_service(db_session, providers=[Broken(t) for t in types])
        result = service.list_notifications(today=TODAY)
        assert result.items == [] and result.errors == types

    def test_resolved_ack_records_are_cleaned_but_not_for_failed_types(self, db_session, client_row):
        ack_repo = NotificationAckRepository(db_session)
        ack_repo.upsert("INVOICE_DUE", 999, "UPCOMING", d(1), now_iso())
        ack_repo.upsert("QUOTE_EXPIRY", 998, "UPCOMING", d(1), now_iso())
        db_session.commit()

        class Broken:
            source_type = "QUOTE_EXPIRY"

            def collect(self, today):
                raise RuntimeError("boom")

        service = build_service(db_session)
        service.providers = [p if p.source_type != "QUOTE_EXPIRY" else Broken() for p in service.providers]
        service.list_notifications(today=TODAY)
        assert ack_repo.find("INVOICE_DUE", 999) is None
        assert ack_repo.find("QUOTE_EXPIRY", 998) is not None

    def test_ack_removed_when_payment_resolves_then_reappears_if_unpaid_again(self, db_session, client_row):
        inv = make_invoice(db_session, client_row, "2026-0001", d(-2))
        service = build_service(db_session)
        service.acknowledge("INVOICE_DUE", inv.id, today=TODAY)
        pay = Payment(invoice_id=inv.id, payment_date="2026-09-18", amount=10000, created_at=now_iso())
        db_session.add(pay)
        db_session.commit()
        assert service.list_notifications(today=TODAY).items == []
        db_session.delete(pay)
        db_session.commit()
        assert len(service.list_notifications(today=TODAY).items) == 1  # 確認済みは残らず再表示


class TestNotificationServiceSummary:
    def test_counts_and_limit(self, db_session, client_row):
        for i in range(4):
            make_invoice(db_session, client_row, f"2026-00{i + 1}", d(-i - 1))
        for i in range(3):
            make_project(db_session, f"P{i}", d(i + 1))
        summary = build_service(db_session).get_summary(limit=5, today=TODAY)
        assert summary.unacknowledged_count == 7
        assert summary.overdue_count == 4
        assert len(summary.items) == 5
        assert all(i.state == "OVERDUE" for i in [x.candidate for x in summary.items[:4]])

    def test_excludes_acknowledged(self, db_session, client_row):
        inv = make_invoice(db_session, client_row, "2026-0001", d(-1))
        make_project(db_session, "P", d(1))
        service = build_service(db_session)
        service.acknowledge("INVOICE_DUE", inv.id, today=TODAY)
        summary = service.get_summary(today=TODAY)
        assert summary.unacknowledged_count == 1
        assert summary.overdue_count == 0

    def test_errors_reported(self, db_session):
        class Broken:
            source_type = "DEADLINE"

            def collect(self, today):
                raise RuntimeError("boom")

        service = build_service(db_session)
        service.providers = [p if p.source_type != "DEADLINE" else Broken() for p in service.providers]
        assert service.get_summary(today=TODAY).errors == ["DEADLINE"]


class TestAcknowledge:
    def test_upsert_records_server_side_state_and_due(self, db_session, client_row):
        inv = make_invoice(db_session, client_row, "2026-0001", d(3))
        service = build_service(db_session)
        service.acknowledge("INVOICE_DUE", inv.id, today=TODAY)
        ack = NotificationAckRepository(db_session).find("INVOICE_DUE", inv.id)
        assert ack.acknowledged_state == "UPCOMING"
        assert ack.acknowledged_due_date == d(3)
        service.acknowledge("INVOICE_DUE", inv.id, today=TODAY)  # 再確認は上書き
        assert len(NotificationAckRepository(db_session).list_by_type("INVOICE_DUE")) == 1

    def test_state_progress_upcoming_to_overdue_reappears(self, db_session, client_row):
        inv = make_invoice(db_session, client_row, "2026-0001", d(1))
        service = build_service(db_session)
        service.acknowledge("INVOICE_DUE", inv.id, today=TODAY)
        assert service.list_notifications(today=TODAY).items == []
        later = TODAY + timedelta(days=2)
        assert len(service.list_notifications(today=later).items) == 1  # 超過に進んだので再表示

    def test_overdue_ack_persists_until_resolved(self, db_session, client_row):
        inv = make_invoice(db_session, client_row, "2026-0001", d(-1))
        service = build_service(db_session)
        service.acknowledge("INVOICE_DUE", inv.id, today=TODAY)
        assert service.list_notifications(today=TODAY + timedelta(days=30)).items == []

    def test_unresolved_source_raises_not_found(self, db_session, client_row):
        inv = make_invoice(db_session, client_row, "2026-0001", d(-1), paid=10000)
        service = build_service(db_session)
        with pytest.raises(NotFoundError, match="既に解消されています"):
            service.acknowledge("INVOICE_DUE", inv.id, today=TODAY)
        with pytest.raises(NotFoundError):
            service.acknowledge("PROJECT_DUE", 12345, today=TODAY)

    def test_recurring_overdue_deadline_rolls_forward_without_ack(self, db_session):
        dl = make_deadline(db_session, "確定申告", d(-10), recurring=1)
        service = build_service(db_session)
        service.acknowledge("DEADLINE", dl.id, today=TODAY)
        db_session.refresh(dl)
        assert dl.due_date == (TODAY - timedelta(days=10)).replace(year=2027).isoformat()
        assert NotificationAckRepository(db_session).find("DEADLINE", dl.id) is None
        assert service.list_notifications(today=TODAY).items == []  # 翌年の期限は7日より先

    def test_recurring_upcoming_deadline_is_just_acknowledged(self, db_session):
        dl = make_deadline(db_session, "確定申告", d(3), recurring=1)
        service = build_service(db_session)
        service.acknowledge("DEADLINE", dl.id, today=TODAY)
        db_session.refresh(dl)
        assert dl.due_date == d(3)
        assert NotificationAckRepository(db_session).find("DEADLINE", dl.id) is not None

    def test_non_recurring_overdue_deadline_stays_and_is_acknowledged(self, db_session):
        dl = make_deadline(db_session, "単発", d(-10), recurring=0)
        service = build_service(db_session)
        service.acknowledge("DEADLINE", dl.id, today=TODAY)
        db_session.refresh(dl)
        assert dl.due_date == d(-10)
        assert service.list_notifications(today=TODAY).items == []
        assert len(service.list_notifications(include_acknowledged=True, today=TODAY).items) == 1

    def test_unacknowledge_deletes_record_and_is_idempotent(self, db_session, client_row):
        inv = make_invoice(db_session, client_row, "2026-0001", d(3))
        service = build_service(db_session)
        service.acknowledge("INVOICE_DUE", inv.id, today=TODAY)
        service.unacknowledge("INVOICE_DUE", inv.id)
        service.unacknowledge("INVOICE_DUE", inv.id)
        assert len(service.list_notifications(today=TODAY).items) == 1


class TestAcknowledgeMissingSource:
    MISSING = "通知の元データが見つかりません"
    RESOLVED = "対象の通知は既に解消されています"

    def test_deleted_source_raises_missing_and_removes_ack(self, db_session, client_row):
        project = make_project(db_session, "P", d(2))
        service = build_service(db_session)
        service.acknowledge("PROJECT_DUE", project.id, today=TODAY)
        ack_repo = NotificationAckRepository(db_session)
        assert len(ack_repo.list_by_type("PROJECT_DUE")) == 1
        db_session.delete(project)
        db_session.commit()
        with pytest.raises(NotFoundError) as exc:
            service.acknowledge("PROJECT_DUE", project.id, today=TODAY)
        assert str(exc.value.message if hasattr(exc.value, "message") else exc.value) == self.MISSING
        assert ack_repo.list_by_type("PROJECT_DUE") == []

    @pytest.mark.parametrize("kind", ["INVOICE_DUE", "QUOTE_EXPIRY", "PROJECT_DUE", "DEADLINE"])
    def test_never_existing_source_is_missing_for_all_kinds(self, db_session, kind):
        with pytest.raises(NotFoundError) as exc:
            build_service(db_session).acknowledge(kind, 99999, today=TODAY)
        assert self.MISSING in str(exc.value.args) + str(getattr(exc.value, "message", ""))

    def test_existing_but_not_candidate_is_resolved(self, db_session):
        far = make_project(db_session, "遠い", d(60))
        with pytest.raises(NotFoundError) as exc:
            build_service(db_session).acknowledge("PROJECT_DUE", far.id, today=TODAY)
        assert self.RESOLVED in str(exc.value.args) + str(getattr(exc.value, "message", ""))

    def test_collect_failure_is_missing_and_ack_kept(self, db_session):
        class Broken:
            source_type = "PROJECT_DUE"

            def collect(self, today):
                raise RuntimeError("boom")

            def source_exists(self, source_id):
                raise AssertionError("must not be called")

        service = build_service(db_session)
        service.providers = [Broken()]
        with pytest.raises(NotFoundError) as exc:
            service.acknowledge("PROJECT_DUE", 1, today=TODAY)
        assert self.MISSING in str(exc.value.args) + str(getattr(exc.value, "message", ""))

    def test_source_exists_on_providers(self, db_session, client_row):
        inv = make_invoice(db_session, client_row, "2026-0001", d(60))
        quote = make_quote(db_session, client_row, "Q1", d(60))
        proj = make_project(db_session, "P", d(60))
        dl = make_deadline(db_session, "D", d(60))
        service = build_service(db_session)
        by_type = {p.source_type: p for p in service.providers}
        assert by_type["INVOICE_DUE"].source_exists(inv.id) and not by_type["INVOICE_DUE"].source_exists(inv.id + 100)
        assert by_type["QUOTE_EXPIRY"].source_exists(quote.id) and not by_type["QUOTE_EXPIRY"].source_exists(quote.id + 100)
        assert by_type["PROJECT_DUE"].source_exists(proj.id) and not by_type["PROJECT_DUE"].source_exists(proj.id + 100)
        assert by_type["DEADLINE"].source_exists(dl.id) and not by_type["DEADLINE"].source_exists(dl.id + 100)
