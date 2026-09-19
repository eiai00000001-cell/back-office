"""手動登録の期限(F-09)API。詳細設計書4.10.5章・7章。"""
from datetime import date

from fastapi import APIRouter, Depends, Response

from app.dependencies import get_deadline_service
from app.schemas.common import EntityId
from app.schemas.deadline import DeadlineCreateRequest, DeadlineResponse, DeadlineUpdateRequest
from app.services.deadline_service import DeadlineService
from app.utils.due_state import judge_due_state

router = APIRouter(prefix="/api/deadlines", tags=["deadlines"])


def _to_response(deadline) -> DeadlineResponse:
    return DeadlineResponse(
        id=deadline.id,
        name=deadline.name,
        due_date=deadline.due_date,
        category=deadline.category,
        memo=deadline.memo,
        is_recurring=bool(deadline.is_recurring),
        due_state=judge_due_state(date.fromisoformat(deadline.due_date), date.today()),
    )


@router.get("", response_model=list[DeadlineResponse])
def list_deadlines(service: DeadlineService = Depends(get_deadline_service)):
    return [_to_response(d) for d in service.list_deadlines()]


@router.post("", response_model=DeadlineResponse, status_code=201)
def create_deadline(dto: DeadlineCreateRequest, service: DeadlineService = Depends(get_deadline_service)):
    return _to_response(service.create_deadline(dto))


@router.get("/{deadline_id}", response_model=DeadlineResponse)
def get_deadline(deadline_id: EntityId, service: DeadlineService = Depends(get_deadline_service)):
    return _to_response(service.get_deadline(deadline_id))


@router.put("/{deadline_id}", response_model=DeadlineResponse)
def update_deadline(
    deadline_id: EntityId, dto: DeadlineUpdateRequest, service: DeadlineService = Depends(get_deadline_service)
):
    return _to_response(service.update_deadline(deadline_id, dto))


@router.delete("/{deadline_id}", status_code=204)
def delete_deadline(deadline_id: EntityId, service: DeadlineService = Depends(get_deadline_service)):
    service.delete_deadline(deadline_id)
    return Response(status_code=204)
