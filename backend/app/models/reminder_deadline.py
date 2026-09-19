from sqlalchemy import CheckConstraint, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReminderDeadline(Base):
    """手動登録の期限(F-09、詳細設計書6.5章)。"""

    __tablename__ = "reminder_deadlines"
    __table_args__ = (
        CheckConstraint("category IN ('TAX_FILING','CONTRACT_RENEWAL','OTHER')", name="ck_reminder_deadlines_category"),
        CheckConstraint("is_recurring IN (0,1)", name="ck_reminder_deadlines_is_recurring"),
        Index("idx_reminder_deadlines_due_date", "due_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    due_date: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False, default="OTHER", server_default="OTHER")
    memo: Mapped[str | None] = mapped_column(String, nullable=True)
    is_recurring: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)
