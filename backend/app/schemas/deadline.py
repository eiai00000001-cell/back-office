import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.enums import DeadlineCategory

_ISO_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
_DATE_MESSAGE = "期限日は日付(YYYY-MM-DD)で入力してください"


class DeadlineCreateRequest(BaseModel):
    # 未指定でも「入力してください」の日本語メッセージになるよう、既定値+validate_default で検証する
    name: str = Field(default="", max_length=100, validate_default=True)
    due_date: str = Field(default="", validate_default=True)
    category: DeadlineCategory = DeadlineCategory.OTHER
    memo: str | None = Field(default=None, max_length=500)
    is_recurring: bool = False

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> object:
        if not isinstance(value, str) or value.strip() == "":
            raise ValueError("名称を入力してください")
        stripped = value.strip()
        if len(stripped) > 100:
            raise ValueError("名称は100文字以内で入力してください")
        return stripped

    @field_validator("due_date", mode="before")
    @classmethod
    def validate_due_date(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            raise ValueError("期限日を入力してください")
        text = str(value).strip()
        if not _ISO_DATE_PATTERN.fullmatch(text):
            raise ValueError(_DATE_MESSAGE)
        try:
            return date.fromisoformat(text).isoformat()
        except ValueError as exc:
            raise ValueError(_DATE_MESSAGE) from exc


class DeadlineUpdateRequest(DeadlineCreateRequest):
    pass


class DeadlineResponse(BaseModel):
    id: int
    name: str
    due_date: str
    category: DeadlineCategory
    memo: str | None
    is_recurring: bool
    due_state: Literal["OVERDUE", "UPCOMING"] | None = None

    model_config = {"from_attributes": True}
