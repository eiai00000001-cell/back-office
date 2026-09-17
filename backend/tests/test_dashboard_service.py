"""財務ダッシュボード(F-07)。詳細設計書4.8章。DashboardServiceおよび関連リポジトリ集計メソッドのテスト。"""
from datetime import date

from app.models.client import Client
from app.models.expense import Expense
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.quote import Quote
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.quote_repository import QuoteRepository
from app.services.dashboard_service import DashboardService
from tests.conftest import now_iso

TODAY = date(2026, 9, 17)


def _client(db_session) -> Client:
    c = Client(name="サンプル商事", created_at=now_iso(), updated_at=now_iso())
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


def _invoice(db_session, client_id, number, issue_date, total_amount, source_quote_id=None) -> Invoice:
    inv = Invoice(
        invoice_number=number,
        client_id=client_id,
        issue_date=issue_date,
        due_date=None,
        source_quote_id=source_quote_id,
        subtotal_amount=total_amount,
        tax_amount=0,
        total_amount=total_amount,
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    db_session.add(inv)
    db_session.commit()
    db_session.refresh(inv)
    return inv


def _quote(db_session, client_id, number, issue_date, total_amount, status="CONFIRMED") -> Quote:
    q = Quote(
        quote_number=number,
        client_id=client_id,
        issue_date=issue_date,
        status=status,
        subtotal_amount=total_amount,
        tax_amount=0,
        total_amount=total_amount,
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)
    return q


def _expense(db_session, expense_date, amount, account_category="消耗品費") -> Expense:
    e = Expense(
        expense_date=expense_date,
        account_category=account_category,
        amount=amount,
        tax_category="STANDARD_10",
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    db_session.add(e)
    db_session.commit()
    db_session.refresh(e)
    return e


def _payment(db_session, invoice_id, payment_date, amount) -> Payment:
    p = Payment(invoice_id=invoice_id, payment_date=payment_date, amount=amount, created_at=now_iso())
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def _service(db_session) -> DashboardService:
    return DashboardService(
        InvoiceRepository(db_session),
        PaymentRepository(db_session),
        ExpenseRepository(db_session),
        QuoteRepository(db_session),
    )


class TestSalesAndPaymentsSummary:
    def test_aggregates_sales_by_issue_month_and_fills_missing_months_with_zero(self, db_session):
        client = _client(db_session)
        _invoice(db_session, client.id, "2026-0001", "2026-09-01", 100000)
        _invoice(db_session, client.id, "2026-0002", "2026-09-15", 50000)
        _invoice(db_session, client.id, "2025-0099", "2025-08-01", 999999)  # 対象期間外(範囲外)

        service = _service(db_session)
        result = service.get_sales_and_payments_summary(today=TODAY)

        by_month = {item.month: item.amount for item in result.sales}
        assert by_month["2026-09"] == 150000
        assert len(result.sales) == 12
        assert by_month["2025-10"] == 0  # 実績なしの月は0円補完

    def test_excludes_invoices_with_null_issue_date(self, db_session):
        # F-04変換直後のissue_date未確定請求書は集計対象に含めない(4.8.2章)
        client = _client(db_session)
        _invoice(db_session, client.id, "2026-0003", None, 300000)

        service = _service(db_session)
        result = service.get_sales_and_payments_summary(today=TODAY)
        total = sum(item.amount for item in result.sales)
        assert total == 0

    def test_aggregates_payments_by_payment_date_independent_of_sales(self, db_session):
        client = _client(db_session)
        invoice = _invoice(db_session, client.id, "2026-0004", "2026-08-01", 200000)
        _payment(db_session, invoice.id, "2026-09-10", 120000)

        service = _service(db_session)
        result = service.get_sales_and_payments_summary(today=TODAY)
        payments_by_month = {item.month: item.amount for item in result.payments}
        assert payments_by_month["2026-09"] == 120000
        assert payments_by_month["2026-08"] == 0


class TestExpenseSummary:
    def test_aggregates_monthly_total_with_zero_fill(self, db_session):
        _expense(db_session, "2026-09-05", 30000, account_category="通信費")
        _expense(db_session, "2026-07-10", 20000, account_category="通信費")

        service = _service(db_session)
        result = service.get_expense_summary(today=TODAY)
        by_month = {item.month: item.amount for item in result.monthly}
        assert by_month["2026-09"] == 30000
        assert by_month["2026-07"] == 20000
        assert by_month["2026-06"] == 0
        assert len(result.monthly) == 12

    def test_category_breakdown_excludes_zero_amount_categories(self, db_session):
        _expense(db_session, "2026-09-05", 30000, account_category="通信費")
        _expense(db_session, "2026-09-06", 10000, account_category="消耗品費")

        service = _service(db_session)
        result = service.get_expense_summary(today=TODAY)
        categories = {item.account_category for item in result.by_category}
        assert categories == {"通信費", "消耗品費"}
        totals = {item.account_category: item.total_amount for item in result.by_category}
        assert totals["通信費"] == 30000


class TestProfitLossSummary:
    def test_calculates_sales_minus_expenses_per_month_allowing_negative(self, db_session):
        client = _client(db_session)
        _invoice(db_session, client.id, "2026-0005", "2026-09-01", 100000)
        _expense(db_session, "2026-09-05", 150000)

        service = _service(db_session)
        result = service.get_profit_loss_summary(today=TODAY)
        by_month = {item.month: item.amount for item in result.monthly}
        assert by_month["2026-09"] == -50000
        assert by_month["2026-08"] == 0


class TestQuoteStatusSummary:
    def test_aggregates_monthly_count_and_amount_with_zero_fill(self, db_session):
        client = _client(db_session)
        _quote(db_session, client.id, "2026-0001", "2026-09-01", 100000)
        _quote(db_session, client.id, "2026-0002", "2026-09-10", 200000)

        service = _service(db_session)
        result = service.get_quote_status_summary(today=TODAY)
        by_month = {item.month: item for item in result.monthly}
        assert by_month["2026-09"].count == 2
        assert by_month["2026-09"].total_amount == 300000
        assert by_month["2026-08"].count == 0
        assert by_month["2026-08"].total_amount == 0

    def test_excludes_quotes_with_null_issue_date_from_monthly_and_rate(self, db_session):
        client = _client(db_session)
        _quote(db_session, client.id, "2026-0003", None, 500000)

        service = _service(db_session)
        result = service.get_quote_status_summary(today=TODAY)
        total = sum(item.count for item in result.monthly)
        assert total == 0
        assert result.conversion_rate is None

    def test_conversion_rate_is_none_when_no_quotes_in_period(self, db_session):
        service = _service(db_session)
        result = service.get_quote_status_summary(today=TODAY)
        assert result.conversion_rate is None

    def test_conversion_rate_calculated_from_converted_quotes(self, db_session):
        client = _client(db_session)
        q1 = _quote(db_session, client.id, "2026-0004", "2026-09-01", 100000)
        _quote(db_session, client.id, "2026-0005", "2026-09-02", 100000)
        _invoice(db_session, client.id, "2026-0006", "2026-09-03", 100000, source_quote_id=q1.id)

        service = _service(db_session)
        result = service.get_quote_status_summary(today=TODAY)
        assert result.conversion_rate == 0.5
