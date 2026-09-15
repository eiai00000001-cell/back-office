from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.quote import Quote
from app.models.quote_item import QuoteItem


class QuoteRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_id(self, quote_id: int) -> Quote | None:
        stmt = (
            select(Quote)
            .options(selectinload(Quote.items), selectinload(Quote.client), selectinload(Quote.invoice))
            .where(Quote.id == quote_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_all(self, client_id: int | None = None, status: str | None = None) -> list[Quote]:
        stmt = (
            select(Quote)
            .options(selectinload(Quote.items), selectinload(Quote.client), selectinload(Quote.invoice))
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
