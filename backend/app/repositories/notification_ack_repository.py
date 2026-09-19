from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.notification_acknowledgement import NotificationAcknowledgement as Ack


def delete_acknowledgement(session: Session, source_type: str, source_id: int) -> None:
    """元データ(請求書・見積書・案件・期限)の削除時に、対応する確認済み記録を削除する(詳細設計書4.10.4)。"""
    session.execute(delete(Ack).where(Ack.source_type == source_type, Ack.source_id == source_id))


class NotificationAckRepository:
    def __init__(self, session: Session):
        self.session = session

    def find(self, source_type: str, source_id: int) -> Ack | None:
        stmt = select(Ack).where(Ack.source_type == source_type, Ack.source_id == source_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_type(self, source_type: str) -> list[Ack]:
        stmt = select(Ack).where(Ack.source_type == source_type).order_by(Ack.source_id)
        return list(self.session.execute(stmt).scalars().all())

    def upsert(
        self, source_type: str, source_id: int, state: str, due_date: str, acknowledged_at: str
    ) -> Ack:
        ack = self.find(source_type, source_id)
        if ack is None:
            ack = Ack(source_type=source_type, source_id=source_id)
            self.session.add(ack)
        ack.acknowledged_state = state
        ack.acknowledged_due_date = due_date
        ack.acknowledged_at = acknowledged_at
        self.session.flush()
        return ack

    def delete(self, source_type: str, source_id: int) -> None:
        delete_acknowledgement(self.session, source_type, source_id)
        self.session.flush()

    def delete_not_in(self, source_type: str, keep_ids: set[int] | list[int]) -> None:
        stmt = delete(Ack).where(Ack.source_type == source_type)
        if keep_ids:
            stmt = stmt.where(Ack.source_id.not_in(list(keep_ids)))
        self.session.execute(stmt)
        self.session.flush()
