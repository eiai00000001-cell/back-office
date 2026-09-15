"""FastAPI dependency wiring: repository -> service instantiation per request."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.client_repository import ClientRepository
from app.repositories.company_profile_repository import CompanyProfileRepository
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.quote_repository import QuoteRepository
from app.services.attachment_service import AttachmentService
from app.services.client_service import ClientService
from app.services.company_profile_service import CompanyProfileService
from app.services.expense_service import ExpenseService
from app.services.home_summary_service import HomeSummaryService
from app.services.invoice_service import InvoiceService
from app.services.numbering_service import NumberingService
from app.services.payment_service import PaymentService
from app.services.pdf_generation_service import PdfGenerationService
from app.services.quote_service import QuoteService
from app.services.quote_to_invoice_conversion_service import QuoteToInvoiceConversionService
from app.services.tax_calculation_service import TaxCalculationService


def get_client_service(db: Session = Depends(get_db)) -> ClientService:
    return ClientService(ClientRepository(db))


def get_company_profile_service(db: Session = Depends(get_db)) -> CompanyProfileService:
    return CompanyProfileService(CompanyProfileRepository(db))


def get_numbering_service(db: Session = Depends(get_db)) -> NumberingService:
    return NumberingService(InvoiceRepository(db), QuoteRepository(db))


def get_invoice_service(db: Session = Depends(get_db)) -> InvoiceService:
    return InvoiceService(
        InvoiceRepository(db),
        ClientRepository(db),
        get_numbering_service(db),
        TaxCalculationService(),
    )


def get_quote_service(db: Session = Depends(get_db)) -> QuoteService:
    return QuoteService(
        QuoteRepository(db),
        ClientRepository(db),
        get_numbering_service(db),
        TaxCalculationService(),
    )


def get_conversion_service(db: Session = Depends(get_db)) -> QuoteToInvoiceConversionService:
    return QuoteToInvoiceConversionService(
        QuoteRepository(db), InvoiceRepository(db), get_numbering_service(db)
    )


def get_expense_service(db: Session = Depends(get_db)) -> ExpenseService:
    return ExpenseService(ExpenseRepository(db))


def get_attachment_service() -> AttachmentService:
    return AttachmentService()


def get_payment_service(db: Session = Depends(get_db)) -> PaymentService:
    return PaymentService(PaymentRepository(db))


def get_home_summary_service(db: Session = Depends(get_db)) -> HomeSummaryService:
    return HomeSummaryService(InvoiceRepository(db), get_payment_service(db))


def get_pdf_generation_service(db: Session = Depends(get_db)) -> PdfGenerationService:
    return PdfGenerationService(CompanyProfileRepository(db))
