"""共通集計サービス(F-07/F-10/F-11共用)。詳細設計書4.12.1章。"""
from app.models.client import Client
from app.models.expense import Expense
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.financial_aggregation_service import FinancialAggregationService
from tests.conftest import now_iso


def _seed(db_session):
    c = Client(name="C", created_at=now_iso(), updated_at=now_iso())
    db_session.add(c)
    db_session.flush()
    for n, issue, total in [("1", "2026-08-10", 1000), ("2", "2026-08-20", 500), ("3", "2026-09-01", 700), ("4", None, 999), ("5", "2026-07-31", 42)]:
        db_session.add(Invoice(invoice_number=n, client_id=c.id, issue_date=issue, subtotal_amount=total, tax_amount=0,
                               total_amount=total, created_at=now_iso(), updated_at=now_iso()))
    db_session.flush()
    inv = db_session.query(Invoice).filter_by(invoice_number="1").one()
    db_session.add(Payment(invoice_id=inv.id, payment_date="2026-09-05", amount=300, created_at=now_iso()))
    for date_, cat, amt in [("2026-08-05", "通信費", 100), ("2026-08-06", "通信費", 50), ("2026-08-07", "雑費", 10), ("2026-09-02", "通信費", 20)]:
        db_session.add(Expense(expense_date=date_, account_category=cat, amount=amt, tax_category="STANDARD_10",
                               created_at=now_iso(), updated_at=now_iso()))
    db_session.commit()


def _svc(db_session):
    return FinancialAggregationService(InvoiceRepository(db_session), PaymentRepository(db_session), ExpenseRepository(db_session))


def test_monthly_sales_excludes_null_issue_date_and_out_of_range(db_session):
    _seed(db_session)
    assert _svc(db_session).monthly_sales("2026-08-01", "2026-09-30") == {"2026-08": 1500, "2026-09": 700}


def test_monthly_payments(db_session):
    _seed(db_session)
    assert _svc(db_session).monthly_payments("2026-08-01", "2026-09-30") == {"2026-09": 300}


def test_monthly_expenses_and_by_category(db_session):
    _seed(db_session)
    svc = _svc(db_session)
    assert svc.monthly_expenses("2026-08-01", "2026-09-30") == {"2026-08": 160, "2026-09": 20}
    assert svc.expense_by_category("2026-08-01", "2026-09-30") == {"通信費": 170, "雑費": 10}


def test_monthly_expenses_by_category(db_session):
    _seed(db_session)
    assert _svc(db_session).monthly_expenses_by_category("2026-08-01", "2026-09-30") == {
        "2026-08": {"通信費": 150, "雑費": 10},
        "2026-09": {"通信費": 20},
    }


def test_monthly_profit_loss_is_sales_minus_expenses_and_may_be_negative(db_session):
    _seed(db_session)
    pl = _svc(db_session).monthly_profit_loss("2026-07-01", "2026-09-30")
    assert pl == {"2026-07": 42, "2026-08": 1340, "2026-09": 680}
    assert _svc(db_session).monthly_profit_loss("2026-08-01", "2026-08-31") == {"2026-08": 1340}


def test_profit_loss_negative_month(db_session):
    _seed(db_session)
    db_session.add(Expense(expense_date="2026-06-01", account_category="雑費", amount=5000, tax_category="STANDARD_10",
                           created_at=now_iso(), updated_at=now_iso()))
    db_session.commit()
    assert _svc(db_session).monthly_profit_loss("2026-06-01", "2026-06-30") == {"2026-06": -5000}
