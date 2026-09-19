from sqlalchemy import CheckConstraint, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NotificationAcknowledgement(Base):
    """確認済みの通知の状態(F-09、詳細設計書6.5章)。source_idは種類ごとに参照先が変わるため外部キーを持たない。"""

    __tablename__ = "notification_acknowledgements"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", name="uq_notification_ack_source"),
        CheckConstraint(
            "source_type IN ('INVOICE_DUE','QUOTE_EXPIRY','PROJECT_DUE','DEADLINE')",
            name="ck_notification_ack_source_type",
        ),
        CheckConstraint("acknowledged_state IN ('UPCOMING','OVERDUE')", name="ck_notification_ack_state"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    acknowledged_state: Mapped[str] = mapped_column(String, nullable=False)
    acknowledged_due_date: Mapped[str] = mapped_column(String, nullable=False)
    acknowledged_at: Mapped[str] = mapped_column(String, nullable=False)
