from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.payment import Payment


class PaymentRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_by_invoice(self, invoice_id: int) -> list[Payment]:
        stmt = select(Payment).where(Payment.invoice_id == invoice_id).order_by(Payment.payment_date, Payment.id)
        return list(self.session.execute(stmt).scalars().all())

    def create(self, payment: Payment) -> Payment:
        self.session.add(payment)
        self.session.flush()
        return payment

    def find_by_id(self, payment_id: int) -> Payment | None:
        return self.session.get(Payment, payment_id)

    def delete(self, payment: Payment) -> None:
        self.session.delete(payment)
        self.session.flush()

    def sum_by_invoice(self, invoice_id: int) -> int:
        stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.invoice_id == invoice_id)
        return self.session.execute(stmt).scalar_one()
