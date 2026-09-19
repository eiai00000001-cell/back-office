from typing import Literal

from pydantic import BaseModel

from app.enums import NotificationSourceType
from app.schemas.common import EntityId


class NotificationItemResponse(BaseModel):
    source_type: NotificationSourceType
    source_id: int
    title: str
    due_date: str
    state: Literal["OVERDUE", "UPCOMING"]
    days_diff: int
    link: str
    category: str | None = None
    acknowledged: bool = False


class NotificationListResponse(BaseModel):
    items: list[NotificationItemResponse]
    errors: list[NotificationSourceType]


class NotificationSummaryResponse(BaseModel):
    unacknowledged_count: int
    overdue_count: int
    items: list[NotificationItemResponse]
    errors: list[NotificationSourceType]


class NotificationAcknowledgeRequest(BaseModel):
    source_type: NotificationSourceType
    source_id: EntityId
