"""見積書作成(F-03)。詳細設計書4.3章。"""
from datetime import datetime

from app.exceptions import NotFoundError, ValidationFailedError
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.repositories.client_repository import ClientRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.quote_repository import QuoteRepository
from app.schemas.quote import QuoteCreateRequest, QuoteUpdateRequest
from app.services.numbering_service import NumberingService
from app.services.project_link_service import ensure_project_exists
from app.services.tax_calculation_service import TaxCalculationService


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class QuoteService:
    def __init__(
        self,
        quote_repository: QuoteRepository,
        client_repository: ClientRepository,
        numbering_service: NumberingService,
        tax_calculation_service: TaxCalculationService,
        project_repository: ProjectRepository,
    ):
        self.quote_repository = quote_repository
        self.client_repository = client_repository
        self.numbering_service = numbering_service
        self.tax_calculation_service = tax_calculation_service
        self.project_repository = project_repository

    def _validate_project(self, dto) -> None:
        ensure_project_exists(self.project_repository, dto.project_id)

    def _validate(self, dto: QuoteCreateRequest) -> None:
        if not dto.items:
            raise ValidationFailedError("品目明細を1件以上入力してください")
        if self.client_repository.find_by_id(dto.client_id) is None:
            raise ValidationFailedError("取引先を選択してください")
        if not dto.issue_date:
            raise ValidationFailedError("発行日を入力してください")
        if not dto.expiry_date:
            raise ValidationFailedError("有効期限を入力してください")

    def _calculate_and_build_items(self, dto: QuoteCreateRequest) -> tuple[dict, list[QuoteItem]]:
        raw_items = [
            {"quantity": item.quantity, "unit_price": item.unit_price, "tax_category": item.tax_category.value}
            for item in dto.items
        ]
        totals = self.tax_calculation_service.calculate_totals(raw_items)
        items = [
            QuoteItem(
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

    def create_quote(self, dto: QuoteCreateRequest) -> Quote:
        self._validate(dto)
        self._validate_project(dto)
        totals, items = self._calculate_and_build_items(dto)
        now = _now_iso()
        quote = Quote(
            quote_number=self.numbering_service.generate_number("quote"),
            client_id=dto.client_id,
            project_id=dto.project_id,
            issue_date=dto.issue_date,
            expiry_date=dto.expiry_date,
            status=dto.status.value,
            subtotal_amount=totals["subtotal_amount"],
            tax_amount=totals["tax_amount"],
            total_amount=totals["total_amount"],
            remarks=dto.remarks,
            created_at=now,
            updated_at=now,
        )
        quote.items = items
        return self.quote_repository.create(quote)

    def update_quote(self, quote_id: int, dto: QuoteUpdateRequest) -> Quote:
        quote = self.quote_repository.find_by_id(quote_id)
        if quote is None:
            raise NotFoundError(f"quote {quote_id} not found")
        self._validate(dto)
        self._validate_project(dto)
        totals, items = self._calculate_and_build_items(dto)
        quote.client_id = dto.client_id
        quote.project_id = dto.project_id
        quote.issue_date = dto.issue_date
        quote.expiry_date = dto.expiry_date
        quote.status = dto.status.value
        quote.subtotal_amount = totals["subtotal_amount"]
        quote.tax_amount = totals["tax_amount"]
        quote.total_amount = totals["total_amount"]
        quote.remarks = dto.remarks
        quote.updated_at = _now_iso()
        self.quote_repository.replace_items(quote, items)
        return self.quote_repository.update(quote)

    def get_quote(self, quote_id: int) -> Quote:
        quote = self.quote_repository.find_by_id(quote_id)
        if quote is None:
            raise NotFoundError(f"quote {quote_id} not found")
        return quote

    def list_quotes(self, client_id: int | None = None, status: str | None = None) -> list[Quote]:
        return self.quote_repository.list_all(client_id=client_id, status=status)

    def delete_quote(self, quote_id: int) -> None:
        quote = self.get_quote(quote_id)
        self.quote_repository.delete(quote)
