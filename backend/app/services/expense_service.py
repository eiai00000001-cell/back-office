"""経費管理(F-02)。詳細設計書4.2章。"""
from datetime import datetime

from app.exceptions import NotFoundError, ValidationFailedError
from app.models.expense import Expense
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.expense import CategorySummaryItem, ExpenseCreateRequest, ExpenseUpdateRequest, MonthSummaryItem
from app.services.project_link_service import ensure_project_exists


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _period_bounds(period_from: str | None, period_to: str | None) -> tuple[str | None, str | None]:
    date_from = f"{period_from}-01" if period_from else None
    date_to = f"{period_to}-31" if period_to else None
    return date_from, date_to


class ExpenseService:
    def __init__(self, expense_repository: ExpenseRepository, project_repository: ProjectRepository):
        self.expense_repository = expense_repository
        self.project_repository = project_repository

    def _validate_project(self, dto) -> None:
        ensure_project_exists(self.project_repository, dto.project_id)

    def create_expense(self, dto: ExpenseCreateRequest) -> Expense:
        self._validate_project(dto)
        now = _now_iso()
        expense = Expense(
            expense_date=dto.expense_date,
            account_category=dto.account_category,
            amount=dto.amount,
            tax_category=dto.tax_category.value,
            payee=dto.payee,
            payment_method=dto.payment_method.value if dto.payment_method else None,
            memo=dto.memo,
            project_id=dto.project_id,
            created_at=now,
            updated_at=now,
        )
        return self.expense_repository.create(expense)

    def update_expense(self, expense_id: int, dto: ExpenseUpdateRequest) -> Expense:
        expense = self.expense_repository.find_by_id(expense_id)
        if expense is None:
            raise NotFoundError(f"expense {expense_id} not found")
        self._validate_project(dto)
        expense.expense_date = dto.expense_date
        expense.account_category = dto.account_category
        expense.amount = dto.amount
        expense.tax_category = dto.tax_category.value
        expense.payee = dto.payee
        expense.payment_method = dto.payment_method.value if dto.payment_method else None
        expense.memo = dto.memo
        expense.project_id = dto.project_id
        expense.updated_at = _now_iso()
        return self.expense_repository.update(expense)

    def get_expense(self, expense_id: int) -> Expense:
        expense = self.expense_repository.find_by_id(expense_id)
        if expense is None:
            raise NotFoundError(f"expense {expense_id} not found")
        return expense

    def list_expenses(
        self,
        account_category: str | None = None,
        payment_method: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[Expense]:
        # 詳細設計書3.6章: 期間(From/To)の入力項目定義表「FromがToより後の場合エラー」
        # (レビュー指摘4対応)。
        if date_from and date_to and date_from > date_to:
            raise ValidationFailedError("期間(From)は期間(To)より前の日付を入力してください")
        return self.expense_repository.list_all(
            account_category=account_category,
            payment_method=payment_method,
            date_from=date_from,
            date_to=date_to,
        )

    def delete_expense(self, expense_id: int) -> None:
        expense = self.get_expense(expense_id)
        self.expense_repository.delete(expense)

    def get_summary_by_category(
        self, period_from: str | None = None, period_to: str | None = None
    ) -> list[CategorySummaryItem]:
        date_from, date_to = _period_bounds(period_from, period_to)
        rows = self.expense_repository.aggregate_by_category(date_from, date_to)
        return [
            CategorySummaryItem(account_category=category, count=count, total_amount=total)
            for category, count, total in rows
        ]

    def get_summary_by_month(
        self, period_from: str | None = None, period_to: str | None = None
    ) -> list[MonthSummaryItem]:
        date_from, date_to = _period_bounds(period_from, period_to)
        rows = self.expense_repository.aggregate_by_month(date_from, date_to)
        return [MonthSummaryItem(year_month=year_month, total_amount=total) for year_month, total in rows]
