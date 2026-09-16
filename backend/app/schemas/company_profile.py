import re

from pydantic import BaseModel, Field, field_validator

REGISTRATION_NUMBER_PATTERN = re.compile(r"^T\d{13}$")


class CompanyProfileUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50, description="氏名を入力してください")
    business_name: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=200)
    contact_info: str | None = Field(default=None, max_length=200)
    invoice_registration_number: str | None = Field(default=None)

    # レビュー指摘1対応: Field(description=...)は実際のエラーメッセージにならないため、
    # mode="before"バリデータで詳細設計書の日本語メッセージを明示的に返す。
    @field_validator("name", mode="before")
    @classmethod
    def validate_name_presence(cls, value: object) -> object:
        if not isinstance(value, str) or value.strip() == "":
            raise ValueError("氏名を入力してください")
        return value

    @field_validator("invoice_registration_number")
    @classmethod
    def validate_registration_number(cls, value: str | None) -> str | None:
        if value and not REGISTRATION_NUMBER_PATTERN.match(value):
            raise ValueError("登録番号はTと数字13桁で入力してください")
        return value


class CompanyProfileResponse(BaseModel):
    name: str
    business_name: str | None
    address: str | None
    contact_info: str | None
    invoice_registration_number: str | None

    model_config = {"from_attributes": True}
