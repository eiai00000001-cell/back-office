import re

from pydantic import BaseModel, Field, field_validator

POSTAL_CODE_PATTERN = re.compile(r"^[0-9-]{0,8}$")


class ClientCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="名称を入力してください")
    postal_code: str | None = Field(default=None, max_length=8)
    address: str | None = Field(default=None, max_length=200)
    contact_person: str | None = Field(default=None, max_length=50)
    contact_info: str | None = Field(default=None, max_length=200)

    # レビュー指摘1対応: Field(description=...)は実際のエラーメッセージにならないため、
    # mode="before"バリデータで詳細設計書の日本語メッセージを明示的に返す。
    @field_validator("name", mode="before")
    @classmethod
    def validate_name_presence(cls, value: object) -> object:
        if not isinstance(value, str) or value.strip() == "":
            raise ValueError("名称を入力してください")
        return value

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: str | None) -> str | None:
        if value and not POSTAL_CODE_PATTERN.match(value):
            raise ValueError("郵便番号は数字とハイフンで入力してください")
        return value


class ClientUpdateRequest(ClientCreateRequest):
    pass


class ClientResponse(BaseModel):
    id: int
    name: str
    postal_code: str | None
    address: str | None
    contact_person: str | None
    contact_info: str | None

    model_config = {"from_attributes": True}
