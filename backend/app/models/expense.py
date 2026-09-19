from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expenses_amount"),
        CheckConstraint(
            "tax_category IN ('STANDARD_10','NON_TAXABLE','OUT_OF_SCOPE','NOT_APPLICABLE')",
            name="ck_expenses_tax_category",
        ),
        CheckConstraint(
            "payment_method IN ('CASH','CREDIT_CARD','BANK_TRANSFER','OTHER') OR payment_method IS NULL",
            name="ck_expenses_payment_method",
        ),
        Index("idx_expenses_expense_date", "expense_date"),
        Index("idx_expenses_account_category", "account_category"),
        Index("idx_expenses_project_id", "project_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expense_date: Mapped[str] = mapped_column(String, nullable=False)
    account_category: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_category: Mapped[str] = mapped_column(String, nullable=False)
    payee: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String, nullable=True)
    memo: Mapped[str | None] = mapped_column(String, nullable=True)
    attachment_path: Mapped[str | None] = mapped_column(String, nullable=True)
    attachment_original_name: Mapped[str | None] = mapped_column(String, nullable=True)
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)
    project = relationship("Project")

    @property
    def project_name(self) -> str | None:
        return self.project.name if self.project else None
