from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.enums import PaymentStatus, TaxCategory
from app.schemas.payment import PaymentResponse


class InvoiceItemInput(BaseModel):
    item_name: str = Field(min_length=1, max_length=100, description="品目名を入力してください")
    quantity: Decimal = Field(gt=0, description="数量は0より大きい数値で入力してください")
    unit_price: int = Field(gt=0, lt=10**10, description="単価は0より大きい数値で入力してください")
    tax_category: TaxCategory

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
    client_id: int
    issue_date: str | None = None
    due_date: str | None = None
    items: list[InvoiceItemInput]
    remarks: str | None = Field(default=None, max_length=1000)


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
    payment_status: PaymentStatus
    is_overdue: bool

    model_config = {"from_attributes": True}
