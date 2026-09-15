from datetime import date, timedelta

from app.models.client import Client
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.home_summary_service import HomeSummaryService
from app.services.payment_service import PaymentService
from tests.conftest import now_iso


def _make_client(db_session) -> Client:
    client = Client(name="サンプル商事", created_at=now_iso(), updated_at=now_iso())
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


def _make_invoice(db_session, client_id, number, total_amount, due_date=None) -> Invoice:
    invoice = Invoice(
        invoice_number=number,
        client_id=client_id,
        due_date=due_date,
        total_amount=total_amount,
        subtotal_amount=total_amount,
        tax_amount=0,
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    return invoice


class TestGetSummary:
    def test_counts_unpaid_and_overdue_invoices(self, db_session):
        client = _make_client(db_session)
        past = (date.today() - timedelta(days=1)).isoformat()
        future = (date.today() + timedelta(days=10)).isoformat()

        overdue_unpaid = _make_invoice(db_session, client.id, "2026-0001", 10000, due_date=past)
        not_overdue_unpaid = _make_invoice(db_session, client.id, "2026-0002", 10000, due_date=future)
        paid = _make_invoice(db_session, client.id, "2026-0003", 10000, due_date=past)
        db_session.add(Payment(invoice_id=paid.id, payment_date=now_iso(), amount=10000, created_at=now_iso()))
        db_session.commit()

        service = HomeSummaryService(
            InvoiceRepository(db_session), PaymentService(PaymentRepository(db_session))
        )
        summary = service.get_summary()
        assert summary.unpaid_count == 2
        assert summary.overdue_count == 1

    def test_zero_when_no_invoices(self, db_session):
        service = HomeSummaryService(
            InvoiceRepository(db_session), PaymentService(PaymentRepository(db_session))
        )
        summary = service.get_summary()
        assert summary.unpaid_count == 0
        assert summary.overdue_count == 0
