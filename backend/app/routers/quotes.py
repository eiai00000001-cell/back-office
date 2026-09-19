from fastapi import APIRouter, Depends, Response

from app.dependencies import (
    get_conversion_service,
    get_pdf_generation_service,
    get_payment_service,
    get_project_link_service,
    get_quote_service,
)
from app.enums import QuoteStatus
from app.exceptions import ConflictError
from app.routers.invoices import _to_response as invoice_to_response
from app.schemas.invoice import InvoiceResponse
from app.schemas.project import ProjectLinkRequest
from app.schemas.quote import QuoteCreateRequest, QuoteListItemResponse, QuoteResponse, QuoteUpdateRequest
from app.services.payment_service import PaymentService
from app.services.pdf_generation_service import PdfGenerationService
from app.services.project_link_service import ProjectLinkService
from app.services.quote_service import QuoteService
from app.services.quote_to_invoice_conversion_service import QuoteToInvoiceConversionService
from app.schemas.common import EntityId

router = APIRouter(prefix="/api/quotes", tags=["quotes"])


def _to_response(quote) -> QuoteResponse:
    invoice = quote.invoice
    return QuoteResponse(
        id=quote.id,
        quote_number=quote.quote_number,
        client_id=quote.client_id,
        client_name=quote.client.name if quote.client else "",
        issue_date=quote.issue_date,
        expiry_date=quote.expiry_date,
        status=quote.status,
        items=quote.items,
        subtotal_amount=quote.subtotal_amount,
        tax_amount=quote.tax_amount,
        total_amount=quote.total_amount,
        remarks=quote.remarks,
        project_id=quote.project_id,
        project_name=quote.project_name,
        converted_invoice_id=invoice.id if invoice else None,
        converted_invoice_number=invoice.invoice_number if invoice else None,
    )


def _to_list_item(quote) -> QuoteListItemResponse:
    return QuoteListItemResponse(
        id=quote.id,
        quote_number=quote.quote_number,
        client_id=quote.client_id,
        client_name=quote.client.name if quote.client else "",
        issue_date=quote.issue_date,
        expiry_date=quote.expiry_date,
        total_amount=quote.total_amount,
        status=quote.status,
        project_id=quote.project_id,
        project_name=quote.project_name,
    )


@router.get("", response_model=list[QuoteListItemResponse])
def list_quotes(
    client_id: EntityId | None = None,
    status: QuoteStatus | None = None,
    service: QuoteService = Depends(get_quote_service),
):
    quotes = service.list_quotes(client_id=client_id, status=status.value if status else None)
    return [_to_list_item(quote) for quote in quotes]


@router.post("", response_model=QuoteResponse, status_code=201)
def create_quote(dto: QuoteCreateRequest, service: QuoteService = Depends(get_quote_service)):
    quote = service.create_quote(dto)
    return _to_response(quote)


@router.get("/{quote_id}", response_model=QuoteResponse)
def get_quote(quote_id: EntityId, service: QuoteService = Depends(get_quote_service)):
    quote = service.get_quote(quote_id)
    return _to_response(quote)


@router.put("/{quote_id}", response_model=QuoteResponse)
def update_quote(quote_id: EntityId, dto: QuoteUpdateRequest, service: QuoteService = Depends(get_quote_service)):
    quote = service.update_quote(quote_id, dto)
    return _to_response(quote)


@router.delete("/{quote_id}", status_code=204)
def delete_quote(quote_id: EntityId, service: QuoteService = Depends(get_quote_service)):
    service.delete_quote(quote_id)
    return Response(status_code=204)


@router.get("/{quote_id}/pdf")
def get_quote_pdf(
    quote_id: EntityId,
    service: QuoteService = Depends(get_quote_service),
    pdf_service: PdfGenerationService = Depends(get_pdf_generation_service),
):
    quote = service.get_quote(quote_id)
    pdf_bytes = pdf_service.render_quote_pdf(quote)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="quote_{quote.quote_number}.pdf"'},
    )


@router.post("/{quote_id}/convert-to-invoice", response_model=InvoiceResponse, status_code=201)
def convert_to_invoice(
    quote_id: EntityId,
    conversion_service: QuoteToInvoiceConversionService = Depends(get_conversion_service),
    payment_service: PaymentService = Depends(get_payment_service),
):
    invoice = conversion_service.convert(quote_id)
    return invoice_to_response(invoice, payment_service)


@router.put("/{quote_id}/project", response_model=QuoteResponse)
def link_quote_project(
    quote_id: EntityId,
    dto: ProjectLinkRequest,
    link_service: ProjectLinkService = Depends(get_project_link_service),
):
    return _to_response(link_service.link_quote(quote_id, dto.project_id))
