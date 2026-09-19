from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Quote(Base):
    __tablename__ = "quotes"
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT','CONFIRMED')", name="ck_quotes_status"),
        Index("idx_quotes_client_id", "client_id"),
        Index("idx_quotes_issue_date", "issue_date"),
        Index("idx_quotes_project_id", "project_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quote_number: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.id"), nullable=False)
    issue_date: Mapped[str | None] = mapped_column(String, nullable=True)
    expiry_date: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="DRAFT")
    subtotal_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tax_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remarks: Mapped[str | None] = mapped_column(String, nullable=True)
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    client = relationship("Client", back_populates="quotes")
    items = relationship(
        "QuoteItem", back_populates="quote", cascade="all, delete-orphan", order_by="QuoteItem.sort_order"
    )
    invoice = relationship("Invoice", back_populates="source_quote", uselist=False)
    project = relationship("Project")

    @property
    def project_name(self) -> str | None:
        return self.project.name if self.project else None
