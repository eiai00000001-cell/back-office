"""手動登録の期限(F-09)。詳細設計書4.10.5章。"""
from datetime import date, datetime

from app.exceptions import NotFoundError
from app.models.reminder_deadline import ReminderDeadline
from app.repositories.deadline_repository import DeadlineRepository
from app.repositories.notification_ack_repository import NotificationAckRepository
from app.schemas.deadline import DeadlineCreateRequest, DeadlineUpdateRequest
from app.utils.date_range import add_years

SOURCE_TYPE = "DEADLINE"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class DeadlineService:
    def __init__(self, deadline_repository: DeadlineRepository, ack_repository: NotificationAckRepository):
        self.deadline_repository = deadline_repository
        self.ack_repository = ack_repository

    def get_deadline(self, deadline_id: int) -> ReminderDeadline:
        deadline = self.deadline_repository.find_by_id(deadline_id)
        if deadline is None:
            raise NotFoundError(f"deadline {deadline_id} not found")
        return deadline

    def list_deadlines(self) -> list[ReminderDeadline]:
        return self.deadline_repository.list_all()

    def create_deadline(self, dto: DeadlineCreateRequest) -> ReminderDeadline:
        now = _now_iso()
        deadline = ReminderDeadline(
            name=dto.name,
            due_date=dto.due_date,
            category=dto.category.value,
            memo=dto.memo,
            is_recurring=int(dto.is_recurring),
            created_at=now,
            updated_at=now,
        )
        return self.deadline_repository.create(deadline)

    def update_deadline(self, deadline_id: int, dto: DeadlineUpdateRequest) -> ReminderDeadline:
        deadline = self.get_deadline(deadline_id)
        if deadline.due_date != dto.due_date:
            # 期限日の変更は新しい期限として通知するため、確認済みの記録を破棄する(4.10.5-2)
            self.ack_repository.delete(SOURCE_TYPE, deadline.id)
        deadline.name = dto.name
        deadline.due_date = dto.due_date
        deadline.category = dto.category.value
        deadline.memo = dto.memo
        deadline.is_recurring = int(dto.is_recurring)
        deadline.updated_at = _now_iso()
        return self.deadline_repository.update(deadline)

    def delete_deadline(self, deadline_id: int) -> None:
        deadline = self.get_deadline(deadline_id)
        self.ack_repository.delete(SOURCE_TYPE, deadline.id)
        self.deadline_repository.delete(deadline)

    def roll_forward(self, deadline: ReminderDeadline, today: date | None = None) -> None:
        """毎年繰り返しの期限を、今日以降の直近の同月日(翌年以降)へ更新する(4.10.5-4)。"""
        today = today or date.today()
        original = date.fromisoformat(deadline.due_date)
        n = 1
        new_due = add_years(original, n)
        while new_due < today:
            n += 1
            new_due = add_years(original, n)
        deadline.due_date = new_due.isoformat()
        deadline.updated_at = _now_iso()
        self.deadline_repository.update(deadline)
