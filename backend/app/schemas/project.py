import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.enums import PaymentStatus, ProjectStatus, QuoteStatus
from app.schemas.common import EntityId

_ISO_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
_DUE_DATE_MESSAGE = "納期は日付(YYYY-MM-DD)で入力してください"


class ProjectCreateRequest(BaseModel):
    name: str = Field(max_length=100)
    client_id: EntityId | None = None
    status: ProjectStatus = ProjectStatus.NOT_STARTED
    due_date: str | None = None
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> object:
        if not isinstance(value, str) or value.strip() == "":
            raise ValueError("案件名を入力してください")
        stripped = value.strip()
        if len(stripped) > 100:
            raise ValueError("案件名は100文字以内で入力してください")
        return stripped

    @field_validator("due_date", mode="before")
    @classmethod
    def validate_due_date(cls, value: object) -> object:
        if value is None or value == "":
            return None
        text = str(value).strip()
        # fromisoformat は 20260919 や 2026-W38-1 も受理するため、形式を厳格に検査してから日付妥当性を確認する
        if not _ISO_DATE_PATTERN.fullmatch(text):
            raise ValueError(_DUE_DATE_MESSAGE)
        try:
            return date.fromisoformat(text).isoformat()
        except ValueError as exc:
            raise ValueError(_DUE_DATE_MESSAGE) from exc


class ProjectUpdateRequest(ProjectCreateRequest):
    pass


class ProjectStatusChangeRequest(BaseModel):
    status: ProjectStatus


class ProjectLinkRequest(BaseModel):
    project_id: EntityId | None = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    client_id: int | None
    client_name: str | None
    status: ProjectStatus
    due_date: str | None
    description: str | None

    model_config = {"from_attributes": True}


class ProjectListItemResponse(ProjectResponse):
    quote_count: int
    invoice_count: int
    due_state: Literal["OVERDUE", "UPCOMING"] | None


class ProjectQuoteItem(BaseModel):
    id: int
    quote_number: str
    issue_date: str | None
    expiry_date: str | None
    total_amount: int
    status: QuoteStatus


class ProjectInvoiceItem(BaseModel):
    id: int
    invoice_number: str
    issue_date: str | None
    due_date: str | None
    total_amount: int
    payment_status: PaymentStatus


class ProjectSummary(BaseModel):
    quote_count: int
    quote_total: int
    invoice_count: int
    invoice_total: int
    paid_total: int
    unpaid_total: int


class ProjectDetailResponse(ProjectListItemResponse):
    quotes: list[ProjectQuoteItem]
    invoices: list[ProjectInvoiceItem]
    summary: ProjectSummary
