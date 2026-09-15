from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.enums import PaymentStatus
from app.services.payment_service import PaymentService


def _invoice(total_amount, due_date=None, paid_total=0):
    return SimpleNamespace(
        total_amount=total_amount,
        due_date=due_date,
        payments=[SimpleNamespace(amount=paid_total)] if paid_total else [],
    )


class TestCalculateStatus:
    def test_unpaid_when_no_payments(self):
        service = PaymentService(payment_repository=None)
        invoice = _invoice(total_amount=10000, paid_total=0)
        assert service.calculate_status(invoice) == PaymentStatus.UNPAID

    def test_partially_paid_when_paid_less_than_total(self):
        service = PaymentService(payment_repository=None)
        invoice = _invoice(total_amount=10000, paid_total=5000)
        assert service.calculate_status(invoice) == PaymentStatus.PARTIALLY_PAID

    def test_paid_when_paid_total_equals_total_amount(self):
        service = PaymentService(payment_repository=None)
        invoice = _invoice(total_amount=10000, paid_total=10000)
        assert service.calculate_status(invoice) == PaymentStatus.PAID

    def test_paid_when_paid_total_exceeds_total_amount(self):
        service = PaymentService(payment_repository=None)
        invoice = _invoice(total_amount=10000, paid_total=15000)
        assert service.calculate_status(invoice) == PaymentStatus.PAID


class TestIsOverdue:
    def test_false_when_due_date_is_none(self):
        service = PaymentService(payment_repository=None)
        invoice = _invoice(total_amount=10000, due_date=None)
        assert service.is_overdue(invoice) is False

    def test_false_when_due_date_in_future(self):
        service = PaymentService(payment_repository=None)
        future = (date.today() + timedelta(days=5)).isoformat()
        invoice = _invoice(total_amount=10000, due_date=future)
        assert service.is_overdue(invoice) is False

    def test_true_when_overdue_and_unpaid(self):
        service = PaymentService(payment_repository=None)
        past = (date.today() - timedelta(days=1)).isoformat()
        invoice = _invoice(total_amount=10000, due_date=past, paid_total=0)
        assert service.is_overdue(invoice) is True

    def test_true_when_overdue_and_partially_paid(self):
        service = PaymentService(payment_repository=None)
        past = (date.today() - timedelta(days=1)).isoformat()
        invoice = _invoice(total_amount=10000, due_date=past, paid_total=3000)
        assert service.is_overdue(invoice) is True

    def test_false_when_overdue_but_fully_paid(self):
        service = PaymentService(payment_repository=None)
        past = (date.today() - timedelta(days=1)).isoformat()
        invoice = _invoice(total_amount=10000, due_date=past, paid_total=10000)
        assert service.is_overdue(invoice) is False
