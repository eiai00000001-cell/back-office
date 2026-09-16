from fastapi import APIRouter, Depends, Response, UploadFile
from fastapi.responses import FileResponse

from app.dependencies import get_attachment_service, get_expense_service
from app.exceptions import NotFoundError
from app.schemas.expense import (
    ExpenseCreateRequest,
    ExpenseResponse,
    ExpenseSummaryResponse,
    ExpenseUpdateRequest,
)
from app.services.attachment_service import AttachmentService
from app.services.expense_service import ExpenseService

router = APIRouter(prefix="/api/expenses", tags=["expenses"])


@router.get("", response_model=list[ExpenseResponse])
def list_expenses(
    account_category: str | None = None,
    payment_method: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    service: ExpenseService = Depends(get_expense_service),
):
    return service.list_expenses(
        account_category=account_category,
        payment_method=payment_method,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("", response_model=ExpenseResponse, status_code=201)
def create_expense(dto: ExpenseCreateRequest, service: ExpenseService = Depends(get_expense_service)):
    return service.create_expense(dto)


@router.get("/summary", response_model=ExpenseSummaryResponse)
def get_expense_summary(
    period_from: str | None = None,
    period_to: str | None = None,
    service: ExpenseService = Depends(get_expense_service),
):
    return ExpenseSummaryResponse(
        by_category=service.get_summary_by_category(period_from, period_to),
        by_month=service.get_summary_by_month(period_from, period_to),
    )


@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(expense_id: int, service: ExpenseService = Depends(get_expense_service)):
    return service.get_expense(expense_id)


@router.put("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: int, dto: ExpenseUpdateRequest, service: ExpenseService = Depends(get_expense_service)
):
    return service.update_expense(expense_id, dto)


@router.delete("/{expense_id}", status_code=204)
def delete_expense(
    expense_id: int,
    service: ExpenseService = Depends(get_expense_service),
    attachment_service: AttachmentService = Depends(get_attachment_service),
):
    service.delete_expense(expense_id)
    # DBレコード削除に合わせて添付ファイル実体も削除し、孤立ファイルの蓄積を防ぐ(レビュー指摘10対応)。
    attachment_service.delete_all(expense_id)
    return Response(status_code=204)


@router.post("/{expense_id}/attachment", response_model=ExpenseResponse)
async def upload_attachment(
    expense_id: int,
    file: UploadFile,
    service: ExpenseService = Depends(get_expense_service),
    attachment_service: AttachmentService = Depends(get_attachment_service),
):
    content = await file.read()
    attachment_service.validate(file.filename, size=len(content))
    relative_path = attachment_service.save(expense_id, file.filename, content)
    expense = service.get_expense(expense_id)
    expense.attachment_path = relative_path
    expense.attachment_original_name = file.filename
    service.expense_repository.update(expense)
    return expense


@router.get("/{expense_id}/attachment")
def get_attachment(
    expense_id: int,
    service: ExpenseService = Depends(get_expense_service),
    attachment_service: AttachmentService = Depends(get_attachment_service),
):
    expense = service.get_expense(expense_id)
    if not expense.attachment_path:
        raise NotFoundError(f"expense {expense_id} has no attachment")
    file_path = attachment_service.get_file_path(expense.attachment_path)
    return FileResponse(path=file_path, filename=expense.attachment_original_name)
