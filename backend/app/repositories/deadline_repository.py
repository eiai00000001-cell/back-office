from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reminder_deadline import ReminderDeadline


class DeadlineRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_id(self, deadline_id: int) -> ReminderDeadline | None:
        return self.session.get(ReminderDeadline, deadline_id)

    def list_all(self) -> list[ReminderDeadline]:
        stmt = select(ReminderDeadline).order_by(ReminderDeadline.due_date, ReminderDeadline.id)
        return list(self.session.execute(stmt).scalars().all())

    def create(self, deadline: ReminderDeadline) -> ReminderDeadline:
        self.session.add(deadline)
        self.session.flush()
        return deadline

    def update(self, deadline: ReminderDeadline) -> ReminderDeadline:
        self.session.flush()
        return deadline

    def delete(self, deadline: ReminderDeadline) -> None:
        self.session.delete(deadline)
        self.session.flush()

    def list_due_before(self, before: str) -> list[ReminderDeadline]:
        stmt = (
            select(ReminderDeadline)
            .where(ReminderDeadline.due_date <= before)
            .order_by(ReminderDeadline.due_date, ReminderDeadline.id)
        )
        return list(self.session.execute(stmt).scalars().all())
