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

    def aggregate_amount_by_payment_month(self, date_from: str, date_to: str) -> list[tuple[str, int]]:
        """財務ダッシュボード(F-07)向け月次入金額集計(参考指標)。詳細設計書4.8.2章。"""
        year_month = func.strftime("%Y-%m", Payment.payment_date)
        stmt = (
            select(year_month, func.coalesce(func.sum(Payment.amount), 0))
            .where(Payment.payment_date >= date_from)
            .where(Payment.payment_date <= date_to)
            .group_by(year_month)
            .order_by(year_month)
        )
        return list(self.session.execute(stmt).all())
