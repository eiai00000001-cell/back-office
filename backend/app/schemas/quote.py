from pydantic import BaseModel, Field

from app.enums import QuoteStatus
from app.schemas.invoice import InvoiceItemInput, InvoiceItemResponse


class QuoteCreateRequest(BaseModel):
    client_id: int
    issue_date: str | None = None
    expiry_date: str | None = None
    status: QuoteStatus = QuoteStatus.DRAFT
    items: list[InvoiceItemInput]
    remarks: str | None = Field(default=None, max_length=1000)
    project_id: int | None = None


class QuoteUpdateRequest(QuoteCreateRequest):
    pass


class QuoteResponse(BaseModel):
    id: int
    quote_number: str
    client_id: int
    client_name: str
    issue_date: str | None
    expiry_date: str | None
    status: QuoteStatus
    items: list[InvoiceItemResponse]
    subtotal_amount: int
    tax_amount: int
    total_amount: int
    remarks: str | None
    project_id: int | None = None
    project_name: str | None = None
    converted_invoice_id: int | None
    converted_invoice_number: str | None

    model_config = {"from_attributes": True}


class QuoteListItemResponse(BaseModel):
    id: int
    quote_number: str
    client_id: int
    client_name: str
    issue_date: str | None
    expiry_date: str | None
    total_amount: int
    status: QuoteStatus
    project_id: int | None = None
    project_name: str | None = None

    model_config = {"from_attributes": True}
