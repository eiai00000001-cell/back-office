from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field, field_validator

from app.enums import PaymentStatus, TaxCategory
from app.schemas.payment import PaymentResponse
from app.schemas.common import EntityId


class InvoiceItemInput(BaseModel):
    item_name: str = Field(min_length=1, max_length=100, description="品目名を入力してください")
    quantity: Decimal = Field(gt=0, description="数量は0より大きい数値で入力してください")
    unit_price: int = Field(gt=0, lt=10**10, description="単価は0より大きい数値で入力してください")
    tax_category: TaxCategory

    # mode="before"のバリデータでField(gt=..., description=...)より先に実行させ、
    # Pydanticの定型英語メッセージではなく詳細設計書3.3章・8章の日本語メッセージを
    # そのままRequestValidationErrorのdetailへ載せる(レビュー指摘1対応)。
    @field_validator("item_name", mode="before")
    @classmethod
    def validate_item_name_presence(cls, value: object) -> object:
        if not isinstance(value, str) or value.strip() == "":
            raise ValueError("品目名を入力してください")
        return value

    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity_positive(cls, value: object) -> object:
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("数量は0より大きい数値で入力してください") from exc
        if decimal_value <= 0:
            raise ValueError("数量は0より大きい数値で入力してください")
        return value

    @field_validator("unit_price", mode="before")
    @classmethod
    def validate_unit_price_positive(cls, value: object) -> object:
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("単価は0より大きい数値で入力してください") from exc
        if decimal_value <= 0 or decimal_value >= 10**10:
            raise ValueError("単価は0より大きい数値で入力してください")
        return value

    @field_validator("quantity")
    @classmethod
    def validate_quantity_scale(cls, value: Decimal) -> Decimal:
        exponent = value.as_tuple().exponent
        if isinstance(exponent, int) and exponent < -2:
            raise ValueError("数量は小数第2位までで入力してください")
        if len(value.as_tuple().digits) > 10:
            raise ValueError("数量の桁数が上限を超えています")
        return value


class InvoiceItemResponse(BaseModel):
    id: int
    item_name: str
    quantity: Decimal
    unit_price: int
    tax_category: TaxCategory
    amount: int
    sort_order: int

    model_config = {"from_attributes": True}


class InvoiceCreateRequest(BaseModel):
    client_id: EntityId
    issue_date: str | None = None
    due_date: str | None = None
    items: list[InvoiceItemInput]
    remarks: str | None = Field(default=None, max_length=1000)
    project_id: EntityId | None = None


class InvoiceUpdateRequest(InvoiceCreateRequest):
    pass


class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    client_id: int
    client_name: str
    issue_date: str | None
    due_date: str | None
    source_quote_id: int | None
    project_id: int | None = None
    project_name: str | None = None
    items: list[InvoiceItemResponse]
    subtotal_amount: int
    tax_amount: int
    total_amount: int
    remarks: str | None
    payments: list[PaymentResponse]
    payment_status: PaymentStatus
    is_overdue: bool

    model_config = {"from_attributes": True}


class InvoiceListItemResponse(BaseModel):
    id: int
    invoice_number: str
    client_id: int
    client_name: str
    issue_date: str | None
    due_date: str | None
    total_amount: int
    paid_amount: int
    project_id: int | None = None
    project_name: str | None = None
    payment_status: PaymentStatus
    is_overdue: bool

    model_config = {"from_attributes": True}
