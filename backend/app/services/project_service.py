"""案件・プロジェクト管理(F-08)。詳細設計書4.9章。"""
from dataclasses import dataclass
from datetime import date, datetime

from app.enums import ProjectStatus
from app.exceptions import NotFoundError, UnprocessableError
from app.models.invoice import Invoice
from app.models.project import Project
from app.models.quote import Quote
from app.repositories.client_repository import ClientRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreateRequest, ProjectUpdateRequest
from app.services.payment_service import PaymentService
from app.utils.due_state import DueState, judge_due_state

CLIENT_NOT_FOUND_MESSAGE = "指定された取引先が見つかりません"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class ProjectListItem:
    project: Project
    client_name: str | None
    quote_count: int
    invoice_count: int
    due_state: DueState | None


@dataclass
class ProjectSummaryData:
    quote_count: int
    quote_total: int
    invoice_count: int
    invoice_total: int
    paid_total: int
    unpaid_total: int


@dataclass
class ProjectInvoiceRow:
    invoice: Invoice
    payment_status: str


@dataclass
class ProjectDetail:
    item: ProjectListItem
    quotes: list[Quote]
    invoices: list[ProjectInvoiceRow]
    summary: ProjectSummaryData


def project_due_state(project: Project, today: date) -> DueState | None:
    """完了以外の案件のみ納期状態を判定する(詳細設計書4.9.1)。"""
    if project.status == ProjectStatus.DONE or not project.due_date:
        return None
    return judge_due_state(date.fromisoformat(project.due_date), today)


class ProjectService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        client_repository: ClientRepository,
        payment_service: PaymentService,
    ):
        self.project_repository = project_repository
        self.client_repository = client_repository
        self.payment_service = payment_service

    def _validate_client(self, client_id: int | None) -> None:
        if client_id is not None and self.client_repository.find_by_id(client_id) is None:
            raise UnprocessableError(CLIENT_NOT_FOUND_MESSAGE)

    def _get(self, project_id: int) -> Project:
        project = self.project_repository.find_by_id(project_id)
        if project is None:
            raise NotFoundError(f"project {project_id} not found")
        return project

    def create_project(self, dto: ProjectCreateRequest) -> Project:
        self._validate_client(dto.client_id)
        now = _now_iso()
        project = Project(
            name=dto.name,
            client_id=dto.client_id,
            status=dto.status.value,
            due_date=dto.due_date,
            description=dto.description,
            created_at=now,
            updated_at=now,
        )
        return self.project_repository.create(project)

    def update_project(self, project_id: int, dto: ProjectUpdateRequest) -> Project:
        project = self._get(project_id)
        self._validate_client(dto.client_id)
        project.name = dto.name
        project.client_id = dto.client_id
        project.status = dto.status.value
        project.due_date = dto.due_date
        project.description = dto.description
        project.updated_at = _now_iso()
        return self.project_repository.update(project)

    def change_status(self, project_id: int, status: ProjectStatus) -> Project:
        project = self._get(project_id)
        return self.project_repository.update_status(project, status.value, _now_iso())

    def list_projects(self, status: str | None = None, client_id: int | None = None) -> list[ProjectListItem]:
        today = date.today()
        return [
            ProjectListItem(p, cname, qc, ic, project_due_state(p, today))
            for p, cname, qc, ic in self.project_repository.list_all(status=status, client_id=client_id)
        ]

    def get_project_detail(self, project_id: int) -> ProjectDetail:
        project = self._get(project_id)
        quotes = self.project_repository.list_quotes(project_id)
        invoices = self.project_repository.list_invoices(project_id)
        rows = [ProjectInvoiceRow(i, self.payment_service.calculate_status(i)) for i in invoices]
        paid_by_invoice = [sum(p.amount for p in i.payments) for i in invoices]
        summary = ProjectSummaryData(
            quote_count=len(quotes),
            quote_total=sum(q.total_amount for q in quotes),
            invoice_count=len(invoices),
            invoice_total=sum(i.total_amount for i in invoices),
            paid_total=sum(paid_by_invoice),
            unpaid_total=sum(max(i.total_amount - paid, 0) for i, paid in zip(invoices, paid_by_invoice)),
        )
        item = ProjectListItem(
            project,
            project.client.name if project.client else None,
            len(quotes),
            len(invoices),
            project_due_state(project, date.today()),
        )
        return ProjectDetail(item, quotes, rows, summary)

    def delete_project(self, project_id: int) -> None:
        self.project_repository.delete(self._get(project_id))
