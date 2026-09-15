from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.expense import Expense


class ExpenseRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_id(self, expense_id: int) -> Expense | None:
        return self.session.get(Expense, expense_id)

    def list_all(
        self,
        account_category: str | None = None,
        payment_method: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[Expense]:
        stmt = select(Expense).order_by(Expense.expense_date.desc(), Expense.id.desc())
        if account_category:
            stmt = stmt.where(Expense.account_category == account_category)
        if payment_method:
            stmt = stmt.where(Expense.payment_method == payment_method)
        if date_from:
            stmt = stmt.where(Expense.expense_date >= date_from)
        if date_to:
            stmt = stmt.where(Expense.expense_date <= date_to)
        return list(self.session.execute(stmt).scalars().all())

    def create(self, expense: Expense) -> Expense:
        self.session.add(expense)
        self.session.flush()
        return expense

    def update(self, expense: Expense) -> Expense:
        self.session.flush()
        return expense

    def delete(self, expense: Expense) -> None:
        self.session.delete(expense)
        self.session.flush()

    def aggregate_by_category(self, date_from: str | None, date_to: str | None) -> list[tuple[str, int, int]]:
        stmt = select(
            Expense.account_category,
            func.count(Expense.id),
            func.coalesce(func.sum(Expense.amount), 0),
        ).group_by(Expense.account_category)
        if date_from:
            stmt = stmt.where(Expense.expense_date >= date_from)
        if date_to:
            stmt = stmt.where(Expense.expense_date <= date_to)
        return list(self.session.execute(stmt).all())

    def aggregate_by_month(self, date_from: str | None, date_to: str | None) -> list[tuple[str, int]]:
        year_month = func.strftime("%Y-%m", Expense.expense_date)
        stmt = select(year_month, func.coalesce(func.sum(Expense.amount), 0)).group_by(year_month).order_by(
            year_month
        )
        if date_from:
            stmt = stmt.where(Expense.expense_date >= date_from)
        if date_to:
            stmt = stmt.where(Expense.expense_date <= date_to)
        return list(self.session.execute(stmt).all())
