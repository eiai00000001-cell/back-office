import pytest

from app.enums import ExpenseTaxCategory, PaymentMethod
from app.exceptions import NotFoundError, ValidationFailedError
from app.repositories.expense_repository import ExpenseRepository
from app.schemas.expense import ExpenseCreateRequest
from app.services.expense_service import ExpenseService


def _valid_dto(**overrides) -> ExpenseCreateRequest:
    data = dict(
        expense_date="2026-09-12",
        account_category="消耗品費",
        amount=3300,
        tax_category=ExpenseTaxCategory.STANDARD_10,
        payee="サンプル文具店",
        payment_method=PaymentMethod.CREDIT_CARD,
        memo=None,
    )
    data.update(overrides)
    return ExpenseCreateRequest(**data)


class TestCreateExpense:
    def test_creates_expense(self, db_session):
        service = ExpenseService(ExpenseRepository(db_session))
        expense = service.create_expense(_valid_dto())
        assert expense.id is not None
        assert expense.amount == 3300

    def test_supports_free_text_other_category(self, db_session):
        service = ExpenseService(ExpenseRepository(db_session))
        expense = service.create_expense(_valid_dto(account_category="書籍代"))
        assert expense.account_category == "書籍代"


class TestListExpenses:
    def test_orders_by_expense_date_descending(self, db_session):
        service = ExpenseService(ExpenseRepository(db_session))
        service.create_expense(_valid_dto(expense_date="2026-09-01"))
        service.create_expense(_valid_dto(expense_date="2026-09-12"))
        expenses = service.list_expenses()
        assert [e.expense_date for e in expenses] == ["2026-09-12", "2026-09-01"]

    def test_filters_by_account_category(self, db_session):
        service = ExpenseService(ExpenseRepository(db_session))
        service.create_expense(_valid_dto(account_category="消耗品費"))
        service.create_expense(_valid_dto(account_category="通信費"))
        filtered = service.list_expenses(account_category="通信費")
        assert len(filtered) == 1
        assert filtered[0].account_category == "通信費"

    def test_raises_when_date_from_is_after_date_to(self, db_session):
        """詳細設計書3.6章: 期間(From/To)「FromがToより後の場合エラー」(レビュー指摘4対応)。"""
        service = ExpenseService(ExpenseRepository(db_session))
        with pytest.raises(ValidationFailedError):
            service.list_expenses(date_from="2026-09-30", date_to="2026-09-01")

    def test_allows_date_from_equal_to_date_to(self, db_session):
        service = ExpenseService(ExpenseRepository(db_session))
        service.create_expense(_valid_dto(expense_date="2026-09-12"))
        result = service.list_expenses(date_from="2026-09-12", date_to="2026-09-12")
        assert len(result) == 1


class TestUpdateExpense:
    def test_updates_existing_expense(self, db_session):
        service = ExpenseService(ExpenseRepository(db_session))
        expense = service.create_expense(_valid_dto())
        updated = service.update_expense(expense.id, _valid_dto(amount=5000))
        assert updated.amount == 5000

    def test_raises_not_found_for_unknown_id(self, db_session):
        service = ExpenseService(ExpenseRepository(db_session))
        with pytest.raises(NotFoundError):
            service.update_expense(9999, _valid_dto())


class TestExpenseSummary:
    def test_summary_by_category_and_month(self, db_session):
        service = ExpenseService(ExpenseRepository(db_session))
        service.create_expense(_valid_dto(expense_date="2026-09-01", account_category="消耗品費", amount=1000))
        service.create_expense(_valid_dto(expense_date="2026-09-12", account_category="消耗品費", amount=2000))
        service.create_expense(_valid_dto(expense_date="2026-08-01", account_category="通信費", amount=500))

        by_category = service.get_summary_by_category("2026-08", "2026-09")
        category_map = {c.account_category: c for c in by_category}
        assert category_map["消耗品費"].count == 2
        assert category_map["消耗品費"].total_amount == 3000
        assert category_map["通信費"].total_amount == 500

        by_month = service.get_summary_by_month("2026-08", "2026-09")
        month_map = {m.year_month: m.total_amount for m in by_month}
        assert month_map["2026-09"] == 3000
        assert month_map["2026-08"] == 500
