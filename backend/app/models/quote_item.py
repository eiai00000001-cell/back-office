from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class QuoteItem(Base):
    __tablename__ = "quote_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_quote_items_quantity"),
        CheckConstraint("unit_price > 0", name="ck_quote_items_unit_price"),
        CheckConstraint(
            "tax_category IN ('STANDARD_10','NON_TAXABLE','OUT_OF_SCOPE')",
            name="ck_quote_items_tax_category",
        ),
        Index("idx_quote_items_quote_id", "quote_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quote_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False
    )
    item_name: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_category: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    quote = relationship("Quote", back_populates="items")
