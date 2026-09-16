from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem


class InvoiceRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_id(self, invoice_id: int) -> Invoice | None:
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.items), selectinload(Invoice.payments), selectinload(Invoice.client))
            .where(Invoice.id == invoice_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_all(self, client_id: int | None = None) -> list[Invoice]:
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.items), selectinload(Invoice.payments), selectinload(Invoice.client))
            .order_by(Invoice.id.desc())
        )
        if client_id is not None:
            stmt = stmt.where(Invoice.client_id == client_id)
        return list(self.session.execute(stmt).scalars().all())

    def create(self, invoice: Invoice) -> Invoice:
        self.session.add(invoice)
        self.session.flush()
        return invoice

    def update(self, invoice: Invoice) -> Invoice:
        self.session.flush()
        return invoice

    def delete(self, invoice: Invoice) -> None:
        self.session.delete(invoice)
        self.session.flush()

    def exists_by_source_quote_id(self, quote_id: int) -> bool:
        # 詳細設計書5.3章のメソッド一覧・4.4章シーケンス図に記載されている存在チェック用メソッド。
        # 実装上、QuoteToInvoiceConversionServiceは変換済み請求書の番号を確認メッセージに含める
        # 必要があるため、存在有無だけでなくレコード自体を取得できる find_by_source_quote_id を
        # 代わりに使用している(実質的に本メソッドの用途を包含する)。設計書との対応関係を明確に
        # するため、デッドコードとして削除せずコメント付きで残す(レビュー指摘8対応)。
        stmt = select(Invoice.id).where(Invoice.source_quote_id == quote_id)
        return self.session.execute(stmt).scalar_one_or_none() is not None

    def find_by_source_quote_id(self, quote_id: int) -> Invoice | None:
        stmt = select(Invoice).where(Invoice.source_quote_id == quote_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def max_number_seq(self, year: int) -> int:
        prefix = f"{year}-"
        stmt = select(func.max(Invoice.invoice_number)).where(Invoice.invoice_number.like(f"{prefix}%"))
        max_number = self.session.execute(stmt).scalar_one_or_none()
        if not max_number:
            return 0
        try:
            return int(max_number.split("-")[1])
        except (IndexError, ValueError):
            return 0

    def replace_items(self, invoice: Invoice, items: list[InvoiceItem]) -> None:
        invoice.items.clear()
        self.session.flush()
        for item in items:
            invoice.items.append(item)
        self.session.flush()
