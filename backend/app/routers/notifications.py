"""通知(F-09)API。詳細設計書4.10.6章・7章。"""
from fastapi import APIRouter, Depends, Response

from app.dependencies import get_notification_service
from app.schemas.notification import (
    NotificationAcknowledgeRequest,
    NotificationItemResponse,
    NotificationListResponse,
    NotificationSummaryResponse,
)
from app.services.notification_service import NotificationItem, NotificationService

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _to_item(item: NotificationItem) -> NotificationItemResponse:
    c = item.candidate
    return NotificationItemResponse(
        source_type=c.source_type,
        source_id=c.source_id,
        title=c.title,
        due_date=c.due_date.isoformat(),
        state=c.state,
        days_diff=c.days_diff,
        link=c.link,
        category=c.category,
        acknowledged=item.acknowledged,
    )


@router.get("", response_model=NotificationListResponse)
def list_notifications(include_acknowledged: bool = False, service: NotificationService = Depends(get_notification_service)):
    result = service.list_notifications(include_acknowledged=include_acknowledged)
    return NotificationListResponse(items=[_to_item(i) for i in result.items], errors=result.errors)


@router.get("/summary", response_model=NotificationSummaryResponse)
def get_notification_summary(service: NotificationService = Depends(get_notification_service)):
    result = service.get_summary()
    return NotificationSummaryResponse(
        unacknowledged_count=result.unacknowledged_count,
        overdue_count=result.overdue_count,
        items=[_to_item(i) for i in result.items],
        errors=result.errors,
    )


@router.post("/acknowledge", status_code=204)
def acknowledge(dto: NotificationAcknowledgeRequest, service: NotificationService = Depends(get_notification_service)):
    service.acknowledge(dto.source_type.value, dto.source_id)
    return Response(status_code=204)


@router.delete("/acknowledge", status_code=204)
def unacknowledge(dto: NotificationAcknowledgeRequest, service: NotificationService = Depends(get_notification_service)):
    service.unacknowledge(dto.source_type.value, dto.source_id)
    return Response(status_code=204)
