from fastapi import APIRouter, Depends, Response

from app.dependencies import (
    get_invoice_service,
    get_project_link_service,
    get_pdf_generation_service,
    get_payment_service,
)
from app.enums import PaymentStatus
from app.schemas.invoice import InvoiceCreateRequest, InvoiceListItemResponse, InvoiceResponse, InvoiceUpdateRequest
from app.schemas.project import ProjectLinkRequest
from app.services.invoice_service import InvoiceService
from app.services.payment_service import PaymentService
from app.services.pdf_generation_service import PdfGenerationService
from app.services.project_link_service import ProjectLinkService

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


def _to_response(invoice, payment_service: PaymentService) -> InvoiceResponse:
    return InvoiceResponse(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        client_id=invoice.client_id,
        client_name=invoice.client.name if invoice.client else "",
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        source_quote_id=invoice.source_quote_id,
        project_id=invoice.project_id,
        project_name=invoice.project_name,
        items=invoice.items,
        subtotal_amount=invoice.subtotal_amount,
        tax_amount=invoice.tax_amount,
        total_amount=invoice.total_amount,
        remarks=invoice.remarks,
        payments=invoice.payments,
        payment_status=payment_service.calculate_status(invoice),
        is_overdue=payment_service.is_overdue(invoice),
    )


def _to_list_item(invoice, payment_service: PaymentService) -> InvoiceListItemResponse:
    return InvoiceListItemResponse(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        client_id=invoice.client_id,
        client_name=invoice.client.name if invoice.client else "",
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        total_amount=invoice.total_amount,
        paid_amount=sum(p.amount for p in invoice.payments),
        project_id=invoice.project_id,
        project_name=invoice.project_name,
        payment_status=payment_service.calculate_status(invoice),
        is_overdue=payment_service.is_overdue(invoice),
    )


@router.get("", response_model=list[InvoiceListItemResponse])
def list_invoices(
    client_id: int | None = None,
    payment_status: PaymentStatus | None = None,
    service: InvoiceService = Depends(get_invoice_service),
    payment_service: PaymentService = Depends(get_payment_service),
):
    invoices = service.list_invoices(client_id=client_id)
    items = [_to_list_item(invoice, payment_service) for invoice in invoices]
    if payment_status is not None:
        items = [item for item in items if item.payment_status == payment_status]
    return items


@router.post("", response_model=InvoiceResponse, status_code=201)
def create_invoice(
    dto: InvoiceCreateRequest,
    service: InvoiceService = Depends(get_invoice_service),
    payment_service: PaymentService = Depends(get_payment_service),
):
    invoice = service.create_invoice(dto)
    return _to_response(invoice, payment_service)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    service: InvoiceService = Depends(get_invoice_service),
    payment_service: PaymentService = Depends(get_payment_service),
):
    invoice = service.get_invoice(invoice_id)
    return _to_response(invoice, payment_service)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: int,
    dto: InvoiceUpdateRequest,
    service: InvoiceService = Depends(get_invoice_service),
    payment_service: PaymentService = Depends(get_payment_service),
):
    invoice = service.update_invoice(invoice_id, dto)
    return _to_response(invoice, payment_service)


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: int, service: InvoiceService = Depends(get_invoice_service)):
    service.delete_invoice(invoice_id)
    return Response(status_code=204)


@router.get("/{invoice_id}/pdf")
def get_invoice_pdf(
    invoice_id: int,
    service: InvoiceService = Depends(get_invoice_service),
    pdf_service: PdfGenerationService = Depends(get_pdf_generation_service),
):
    invoice = service.get_invoice(invoice_id)
    pdf_bytes = pdf_service.render_invoice_pdf(invoice)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="invoice_{invoice.invoice_number}.pdf"'},
    )


@router.put("/{invoice_id}/project", response_model=InvoiceResponse)
def link_invoice_project(
    invoice_id: int,
    dto: ProjectLinkRequest,
    link_service: ProjectLinkService = Depends(get_project_link_service),
    payment_service: PaymentService = Depends(get_payment_service),
):
    """案件の紐付け・解除(project_idのみ更新。日付必須の通常保存バリデーションは適用しない。4.9.5)。"""
    return _to_response(link_service.link_invoice(invoice_id, dto.project_id), payment_service)
