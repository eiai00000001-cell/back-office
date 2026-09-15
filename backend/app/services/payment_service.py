"""入金・売掛金管理(F-05)。詳細設計書4.5章。"""
from datetime import date

from app.enums import PaymentStatus
from app.exceptions import ConflictError
from app.models.payment import Payment
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import PaymentCreateRequest


class PaymentOverpaymentConfirmationRequiredError(ConflictError):
    """入金額合計が請求金額を超過する場合、force=Trueでの再送が必要。"""


class PaymentService:
    def __init__(self, payment_repository: PaymentRepository | None):
        self.payment_repository = payment_repository

    def calculate_status(self, invoice) -> PaymentStatus:
        paid_total = sum(p.amount for p in invoice.payments)
        if paid_total == 0:
            return PaymentStatus.UNPAID
        if paid_total < invoice.total_amount:
            return PaymentStatus.PARTIALLY_PAID
        return PaymentStatus.PAID

    def is_overdue(self, invoice) -> bool:
        if invoice.due_date is None:
            return False
        if date.today().isoformat() <= invoice.due_date:
            return False
        status = self.calculate_status(invoice)
        return status in (PaymentStatus.UNPAID, PaymentStatus.PARTIALLY_PAID)

    def record_payment(self, invoice, dto: PaymentCreateRequest, force: bool = False) -> Payment:
        force = force or dto.force
        existing_total = self.payment_repository.sum_by_invoice(invoice.id)
        if existing_total + dto.amount > invoice.total_amount and not force:
            raise PaymentOverpaymentConfirmationRequiredError(
                "入金額の合計が請求金額を超過します。登録しますか?"
            )
        payment = Payment(
            invoice_id=invoice.id,
            payment_date=dto.payment_date,
            amount=dto.amount,
            remarks=dto.remarks,
            created_at=_now_iso(),
        )
        return self.payment_repository.create(payment)


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")
