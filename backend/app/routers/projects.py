from fastapi import APIRouter, Depends, Response

from app.dependencies import get_project_service
from app.enums import ProjectStatus
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectDetailResponse,
    ProjectInvoiceItem,
    ProjectListItemResponse,
    ProjectQuoteItem,
    ProjectResponse,
    ProjectStatusChangeRequest,
    ProjectSummary,
    ProjectUpdateRequest,
)
from app.services.project_service import ProjectDetail, ProjectListItem, ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _to_response(project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        client_id=project.client_id,
        client_name=project.client.name if project.client else None,
        status=project.status,
        due_date=project.due_date,
        description=project.description,
    )


def _to_list_item(item: ProjectListItem) -> ProjectListItemResponse:
    base = _to_response(item.project)
    return ProjectListItemResponse(
        **base.model_dump(),
        quote_count=item.quote_count,
        invoice_count=item.invoice_count,
        due_state=item.due_state,
    )


def _to_detail(detail: ProjectDetail) -> ProjectDetailResponse:
    base = _to_list_item(detail.item)
    return ProjectDetailResponse(
        **base.model_dump(),
        quotes=[
            ProjectQuoteItem(
                id=q.id,
                quote_number=q.quote_number,
                issue_date=q.issue_date,
                expiry_date=q.expiry_date,
                total_amount=q.total_amount,
                status=q.status,
            )
            for q in detail.quotes
        ],
        invoices=[
            ProjectInvoiceItem(
                id=row.invoice.id,
                invoice_number=row.invoice.invoice_number,
                issue_date=row.invoice.issue_date,
                due_date=row.invoice.due_date,
                total_amount=row.invoice.total_amount,
                payment_status=row.payment_status,
            )
            for row in detail.invoices
        ],
        summary=ProjectSummary(**vars(detail.summary)),
    )


@router.get("", response_model=list[ProjectListItemResponse])
def list_projects(
    status: ProjectStatus | None = None,
    client_id: int | None = None,
    service: ProjectService = Depends(get_project_service),
):
    items = service.list_projects(status=status.value if status else None, client_id=client_id)
    return [_to_list_item(item) for item in items]


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(dto: ProjectCreateRequest, service: ProjectService = Depends(get_project_service)):
    return _to_response(service.create_project(dto))


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(project_id: int, service: ProjectService = Depends(get_project_service)):
    return _to_detail(service.get_project_detail(project_id))


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int, dto: ProjectUpdateRequest, service: ProjectService = Depends(get_project_service)
):
    return _to_response(service.update_project(project_id, dto))


@router.patch("/{project_id}/status", response_model=ProjectResponse)
def change_project_status(
    project_id: int, dto: ProjectStatusChangeRequest, service: ProjectService = Depends(get_project_service)
):
    return _to_response(service.change_status(project_id, dto.status))


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, service: ProjectService = Depends(get_project_service)):
    service.delete_project(project_id)
    return Response(status_code=204)
