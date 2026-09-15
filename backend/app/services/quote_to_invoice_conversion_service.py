"""見積→請求の自動変換(F-04)。詳細設計書4.4章。"""
from datetime import datetime

from app.exceptions import ConflictError, NotFoundError
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.quote_repository import QuoteRepository
from app.services.numbering_service import NumberingService


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ConversionConflictError(ConflictError):
    """変換元見積書が既に請求書へ変換済みの場合。"""

    def __init__(self, invoice_number: str):
        self.invoice_number = invoice_number
        super().__init__(
            f"この見積書は既に請求書(No.{invoice_number})に変換済みのため、再変換できません"
        )


class QuoteToInvoiceConversionService:
    def __init__(
        self,
        quote_repository: QuoteRepository,
        invoice_repository: InvoiceRepository,
        numbering_service: NumberingService,
    ):
        self.quote_repository = quote_repository
        self.invoice_repository = invoice_repository
        self.numbering_service = numbering_service

    def convert(self, quote_id: int) -> Invoice:
        quote = self.quote_repository.find_by_id(quote_id)
        if quote is None:
            raise NotFoundError(f"quote {quote_id} not found")

        existing_invoice = self.invoice_repository.find_by_source_quote_id(quote_id)
        if existing_invoice is not None:
            raise ConversionConflictError(existing_invoice.invoice_number)

        now = _now_iso()
        invoice = Invoice(
            invoice_number=self.numbering_service.generate_number("invoice"),
            client_id=quote.client_id,
            issue_date=None,
            due_date=None,
            source_quote_id=quote.id,
            subtotal_amount=quote.subtotal_amount,
            tax_amount=quote.tax_amount,
            total_amount=quote.total_amount,
            remarks=None,
            created_at=now,
            updated_at=now,
        )
        invoice.items = [
            InvoiceItem(
                item_name=item.item_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                tax_category=item.tax_category,
                amount=item.amount,
                sort_order=item.sort_order,
            )
            for item in quote.items
        ]
        return self.invoice_repository.create(invoice)
