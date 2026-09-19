from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.invoice import Invoice
from app.models.quote import Quote
from app.models.quote_item import QuoteItem


class QuoteRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_id(self, quote_id: int) -> Quote | None:
        stmt = (
            select(Quote)
            .options(selectinload(Quote.items), selectinload(Quote.client), selectinload(Quote.invoice), selectinload(Quote.project))
            .where(Quote.id == quote_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_all(self, client_id: int | None = None, status: str | None = None) -> list[Quote]:
        stmt = (
            select(Quote)
            .options(selectinload(Quote.items), selectinload(Quote.client), selectinload(Quote.invoice), selectinload(Quote.project))
            .order_by(Quote.id.desc())
        )
        if client_id is not None:
            stmt = stmt.where(Quote.client_id == client_id)
        if status is not None:
            stmt = stmt.where(Quote.status == status)
        return list(self.session.execute(stmt).scalars().all())

    def create(self, quote: Quote) -> Quote:
        self.session.add(quote)
        self.session.flush()
        return quote

    def update(self, quote: Quote) -> Quote:
        self.session.flush()
        return quote

    def delete(self, quote: Quote) -> None:
        self.session.delete(quote)
        self.session.flush()

    def max_number_seq(self, year: int) -> int:
        prefix = f"{year}-"
        stmt = select(func.max(Quote.quote_number)).where(Quote.quote_number.like(f"{prefix}%"))
        max_number = self.session.execute(stmt).scalar_one_or_none()
        if not max_number:
            return 0
        try:
            return int(max_number.split("-")[1])
        except (IndexError, ValueError):
            return 0

    def replace_items(self, quote: Quote, items: list[QuoteItem]) -> None:
        quote.items.clear()
        self.session.flush()
        for item in items:
            quote.items.append(item)
        self.session.flush()

    def aggregate_count_and_amount_by_issue_month(self, date_from: str, date_to: str) -> list[tuple[str, int, int]]:
        """財務ダッシュボード(F-07)向け月次見積件数・金額集計。詳細設計書4.8.5章。

        issue_dateがNULLの見積書は集計対象に含めない。
        """
        year_month = func.strftime("%Y-%m", Quote.issue_date)
        stmt = (
            select(year_month, func.count(Quote.id), func.coalesce(func.sum(Quote.total_amount), 0))
            .where(Quote.issue_date.is_not(None))
            .where(Quote.issue_date >= date_from)
            .where(Quote.issue_date <= date_to)
            .group_by(year_month)
            .order_by(year_month)
        )
        return list(self.session.execute(stmt).all())

    def count_in_period(self, date_from: str, date_to: str) -> int:
        """財務ダッシュボード(F-07)向け見積成約率の分母。詳細設計書4.8.5章。"""
        stmt = (
            select(func.count(Quote.id))
            .where(Quote.issue_date.is_not(None))
            .where(Quote.issue_date >= date_from)
            .where(Quote.issue_date <= date_to)
        )
        return self.session.execute(stmt).scalar_one()

    def count_converted_in_period(self, date_from: str, date_to: str) -> int:
        """財務ダッシュボード(F-07)向け見積成約率の分子(変換済み件数)。詳細設計書4.8.5章。"""
        converted = exists().where(Invoice.source_quote_id == Quote.id)
        stmt = (
            select(func.count(Quote.id))
            .where(Quote.issue_date.is_not(None))
            .where(Quote.issue_date >= date_from)
            .where(Quote.issue_date <= date_to)
            .where(converted)
        )
        return self.session.execute(stmt).scalar_one()
