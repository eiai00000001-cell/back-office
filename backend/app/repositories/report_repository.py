"""レポート出力(F-10)用の読み取り専用クエリ。詳細設計書4.11.2〜4.11.6章。"""
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.models.expense import Expense
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.quote import Quote


@dataclass
class ProjectSummaryRow:
    name: str
    client_name: str | None
    status: str
    due_date: str | None
    quote_count: int
    quote_amount: int
    invoice_count: int
    invoice_amount: int


# 詳細設計書4.11.4のSQL(対象案件の抽出と、期間内の見積書・請求書の件数・金額)
_PROJECT_SUMMARY_SQL = text(
    """
    SELECT p.name, c.name AS client_name, p.status, p.due_date,
           (SELECT COUNT(*) FROM quotes q WHERE q.project_id = p.id AND q.issue_date BETWEEN :from AND :to),
           (SELECT COALESCE(SUM(q.total_amount),0) FROM quotes q WHERE q.project_id = p.id AND q.issue_date BETWEEN :from AND :to),
           (SELECT COUNT(*) FROM invoices i WHERE i.project_id = p.id AND i.issue_date BETWEEN :from AND :to),
           (SELECT COALESCE(SUM(i.total_amount),0) FROM invoices i WHERE i.project_id = p.id AND i.issue_date BETWEEN :from AND :to)
    FROM projects p LEFT JOIN clients c ON c.id = p.client_id
    WHERE p.due_date BETWEEN :from AND :to
       OR EXISTS (SELECT 1 FROM invoices i WHERE i.project_id = p.id AND i.issue_date BETWEEN :from AND :to)
    ORDER BY p.due_date IS NULL, p.due_date, p.id
    """
)


class ReportRepository:
    def __init__(self, session: Session):
        self.session = session

    def invoices_in_period(self, date_from: str, date_to: str) -> list[Invoice]:
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.client), selectinload(Invoice.project), selectinload(Invoice.payments))
            .where(Invoice.issue_date.is_not(None), Invoice.issue_date >= date_from, Invoice.issue_date <= date_to)
            .order_by(Invoice.issue_date, Invoice.invoice_number, Invoice.id)
        )
        return list(self.session.execute(stmt).scalars().all())

    def payments_in_period(self, date_from: str, date_to: str) -> list[tuple[Payment, str]]:
        stmt = (
            select(Payment, Invoice.invoice_number)
            .join(Invoice, Invoice.id == Payment.invoice_id)
            .where(Payment.payment_date >= date_from, Payment.payment_date <= date_to)
            .order_by(Payment.payment_date, Invoice.invoice_number, Payment.id)
        )
        return [(p, number) for p, number in self.session.execute(stmt).all()]

    def quotes_in_period(self, date_from: str, date_to: str) -> list[Quote]:
        stmt = (
            select(Quote)
            .options(selectinload(Quote.client), selectinload(Quote.project))
            .where(Quote.issue_date.is_not(None), Quote.issue_date >= date_from, Quote.issue_date <= date_to)
            .order_by(Quote.issue_date, Quote.quote_number, Quote.id)
        )
        return list(self.session.execute(stmt).scalars().all())

    def expenses_in_period(self, date_from: str, date_to: str) -> list[Expense]:
        stmt = (
            select(Expense)
            .where(Expense.expense_date >= date_from, Expense.expense_date <= date_to)
            .order_by(Expense.expense_date, Expense.id)
        )
        return list(self.session.execute(stmt).scalars().all())

    def project_summaries(self, date_from: str, date_to: str) -> list[ProjectSummaryRow]:
        rows = self.session.execute(_PROJECT_SUMMARY_SQL, {"from": date_from, "to": date_to}).all()
        return [ProjectSummaryRow(*row) for row in rows]
