"""請求書発行(F-01)。詳細設計書4.1章。"""
from datetime import datetime

from app.exceptions import NotFoundError, ValidationFailedError
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.repositories.client_repository import ClientRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.invoice import InvoiceCreateRequest, InvoiceUpdateRequest
from app.services.numbering_service import NumberingService
from app.services.project_link_service import ensure_project_exists
from app.services.tax_calculation_service import TaxCalculationService


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class InvoiceService:
    def __init__(
        self,
        invoice_repository: InvoiceRepository,
        client_repository: ClientRepository,
        numbering_service: NumberingService,
        tax_calculation_service: TaxCalculationService,
        project_repository: ProjectRepository,
    ):
        self.invoice_repository = invoice_repository
        self.client_repository = client_repository
        self.numbering_service = numbering_service
        self.tax_calculation_service = tax_calculation_service
        self.project_repository = project_repository

    def _validate_project(self, dto) -> None:
        ensure_project_exists(self.project_repository, dto.project_id)

    def _validate(self, dto: InvoiceCreateRequest) -> None:
        if not dto.items:
            raise ValidationFailedError("品目明細を1件以上入力してください")
        if self.client_repository.find_by_id(dto.client_id) is None:
            raise ValidationFailedError("取引先を選択してください")
        if not dto.issue_date:
            raise ValidationFailedError("発行日を入力してください")
        if not dto.due_date:
            raise ValidationFailedError("支払期限を入力してください")

    def _calculate_and_build_items(self, dto: InvoiceCreateRequest) -> tuple[dict, list[InvoiceItem]]:
        raw_items = [
            {"quantity": item.quantity, "unit_price": item.unit_price, "tax_category": item.tax_category.value}
            for item in dto.items
        ]
        totals = self.tax_calculation_service.calculate_totals(raw_items)
        items = [
            InvoiceItem(
                item_name=item.item_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                tax_category=item.tax_category.value,
                amount=amount,
                sort_order=index,
            )
            for index, (item, amount) in enumerate(zip(dto.items, totals["item_amounts"]))
        ]
        return totals, items

    def create_invoice(self, dto: InvoiceCreateRequest) -> Invoice:
        self._validate(dto)
        self._validate_project(dto)
        totals, items = self._calculate_and_build_items(dto)
        now = _now_iso()
        invoice = Invoice(
            invoice_number=self.numbering_service.generate_number("invoice"),
            client_id=dto.client_id,
            project_id=dto.project_id,
            issue_date=dto.issue_date,
            due_date=dto.due_date,
            subtotal_amount=totals["subtotal_amount"],
            tax_amount=totals["tax_amount"],
            total_amount=totals["total_amount"],
            remarks=dto.remarks,
            created_at=now,
            updated_at=now,
        )
        invoice.items = items
        return self.invoice_repository.create(invoice)

    def update_invoice(self, invoice_id: int, dto: InvoiceUpdateRequest) -> Invoice:
        invoice = self.invoice_repository.find_by_id(invoice_id)
        if invoice is None:
            raise NotFoundError(f"invoice {invoice_id} not found")
        self._validate(dto)
        self._validate_project(dto)
        totals, items = self._calculate_and_build_items(dto)
        invoice.client_id = dto.client_id
        invoice.project_id = dto.project_id
        invoice.issue_date = dto.issue_date
        invoice.due_date = dto.due_date
        invoice.subtotal_amount = totals["subtotal_amount"]
        invoice.tax_amount = totals["tax_amount"]
        invoice.total_amount = totals["total_amount"]
        invoice.remarks = dto.remarks
        invoice.updated_at = _now_iso()
        self.invoice_repository.replace_items(invoice, items)
        return self.invoice_repository.update(invoice)

    def get_invoice(self, invoice_id: int) -> Invoice:
        invoice = self.invoice_repository.find_by_id(invoice_id)
        if invoice is None:
            raise NotFoundError(f"invoice {invoice_id} not found")
        return invoice

    def list_invoices(self, client_id: int | None = None) -> list[Invoice]:
        return self.invoice_repository.list_all(client_id=client_id)

    def delete_invoice(self, invoice_id: int) -> None:
        invoice = self.get_invoice(invoice_id)
        self.invoice_repository.delete(invoice)
