import pytest

from app.models.client import Client
from app.models.invoice import Invoice
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import PaymentCreateRequest
from app.services.payment_service import PaymentService, PaymentOverpaymentConfirmationRequiredError
from tests.conftest import now_iso


def _make_invoice(db_session, total_amount=10000) -> Invoice:
    client = Client(name="取引先A", created_at=now_iso(), updated_at=now_iso())
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    invoice = Invoice(
        invoice_number="2026-0001",
        client_id=client.id,
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


class TestRecordPayment:
    def test_records_payment_within_total_amount(self, db_session):
        invoice = _make_invoice(db_session, total_amount=10000)
        service = PaymentService(PaymentRepository(db_session))
        dto = PaymentCreateRequest(payment_date="2026-09-01", amount=5000, remarks=None)
        payment = service.record_payment(invoice, dto)
        assert payment.amount == 5000
        assert payment.invoice_id == invoice.id

    def test_raises_confirmation_required_when_overpaying_without_force(self, db_session):
        invoice = _make_invoice(db_session, total_amount=10000)
        service = PaymentService(PaymentRepository(db_session))
        dto = PaymentCreateRequest(payment_date="2026-09-01", amount=15000, remarks=None)
        with pytest.raises(PaymentOverpaymentConfirmationRequiredError):
            service.record_payment(invoice, dto, force=False)

    def test_allows_overpayment_when_forced(self, db_session):
        invoice = _make_invoice(db_session, total_amount=10000)
        service = PaymentService(PaymentRepository(db_session))
        dto = PaymentCreateRequest(payment_date="2026-09-01", amount=15000, remarks=None)
        payment = service.record_payment(invoice, dto, force=True)
        assert payment.amount == 15000
