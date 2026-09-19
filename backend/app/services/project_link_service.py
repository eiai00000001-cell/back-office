"""請求書・見積書・経費の案件紐付け・解除(F-08)。詳細設計書4.9.5章。project_id・updated_atのみを更新する。"""
from datetime import datetime

from app.exceptions import NotFoundError, UnprocessableError
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.quote_repository import QuoteRepository

PROJECT_NOT_FOUND_MESSAGE = "指定された案件が見つかりません。画面を再読み込みしてください"


def ensure_project_exists(project_repository: ProjectRepository, project_id: int | None) -> None:
    if project_id is not None and project_repository.find_by_id(project_id) is None:
        raise UnprocessableError(PROJECT_NOT_FOUND_MESSAGE)


class ProjectLinkService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        invoice_repository: InvoiceRepository,
        quote_repository: QuoteRepository,
        expense_repository: ExpenseRepository,
    ):
        self.project_repository = project_repository
        self.invoice_repository = invoice_repository
        self.quote_repository = quote_repository
        self.expense_repository = expense_repository

    def _link(self, repository, kind: str, document_id: int, project_id: int | None):
        document = repository.find_by_id(document_id)
        if document is None:
            raise NotFoundError(f"{kind} {document_id} not found")
        ensure_project_exists(self.project_repository, project_id)
        document.project_id = project_id
        document.updated_at = datetime.now().isoformat(timespec="seconds")
        repository.update(document)
        self.project_repository.session.refresh(document)
        return document

    def link_invoice(self, invoice_id: int, project_id: int | None):
        return self._link(self.invoice_repository, "invoice", invoice_id, project_id)

    def link_quote(self, quote_id: int, project_id: int | None):
        return self._link(self.quote_repository, "quote", quote_id, project_id)

    def link_expense(self, expense_id: int, project_id: int | None):
        return self._link(self.expense_repository, "expense", expense_id, project_id)
