from fastapi import APIRouter, Depends, Response

from app.dependencies import get_invoice_service, get_payment_service
from app.exceptions import NotFoundError
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import PaymentCreateRequest, PaymentResponse
from app.services.invoice_service import InvoiceService
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/api", tags=["payments"])


@router.get("/invoices/{invoice_id}/payments", response_model=list[PaymentResponse])
def list_payments(
    invoice_id: int,
    invoice_service: InvoiceService = Depends(get_invoice_service),
    payment_service: PaymentService = Depends(get_payment_service),
):
    invoice = invoice_service.get_invoice(invoice_id)
    return payment_service.payment_repository.list_by_invoice(invoice.id)


@router.post("/invoices/{invoice_id}/payments", response_model=PaymentResponse, status_code=201)
def create_payment(
    invoice_id: int,
    dto: PaymentCreateRequest,
    invoice_service: InvoiceService = Depends(get_invoice_service),
    payment_service: PaymentService = Depends(get_payment_service),
):
    invoice = invoice_service.get_invoice(invoice_id)
    return payment_service.record_payment(invoice, dto)


@router.delete("/payments/{payment_id}", status_code=204)
def delete_payment(payment_id: int, payment_service: PaymentService = Depends(get_payment_service)):
    payment = payment_service.payment_repository.find_by_id(payment_id)
    if payment is None:
        raise NotFoundError(f"payment {payment_id} not found")
    payment_service.payment_repository.delete(payment)
    return Response(status_code=204)
