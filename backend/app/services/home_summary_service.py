"""ホーム画面サマリー(F-06)。詳細設計書4.6章。"""
from app.enums import PaymentStatus
from app.repositories.invoice_repository import InvoiceRepository
from app.schemas.home import HomeSummaryResponse
from app.services.payment_service import PaymentService


class HomeSummaryService:
    def __init__(self, invoice_repository: InvoiceRepository, payment_service: PaymentService):
        self.invoice_repository = invoice_repository
        self.payment_service = payment_service

    def get_summary(self) -> HomeSummaryResponse:
        invoices = self.invoice_repository.list_all()
        unpaid_count = 0
        overdue_count = 0
        for invoice in invoices:
            status = self.payment_service.calculate_status(invoice)
            if status in (PaymentStatus.UNPAID, PaymentStatus.PARTIALLY_PAID):
                unpaid_count += 1
                if self.payment_service.is_overdue(invoice):
                    overdue_count += 1
        return HomeSummaryResponse(unpaid_count=unpaid_count, overdue_count=overdue_count)
