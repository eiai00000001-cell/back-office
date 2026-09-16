from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field, field_validator


class PaymentCreateRequest(BaseModel):
    payment_date: str
    amount: int = Field(gt=0, description="入金額は0より大きい数値で入力してください")
    remarks: str | None = Field(default=None, max_length=200)
    force: bool = Field(default=False, description="入金額合計が請求金額を超過する場合の確認済みフラグ")

    # レビュー指摘1対応: Field(description=...)は実際のエラーメッセージにならないため、
    # mode="before"バリデータで詳細設計書の日本語メッセージを明示的に返す。
    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount_positive(cls, value: object) -> object:
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("入金額は0より大きい数値で入力してください") from exc
        if decimal_value <= 0:
            raise ValueError("入金額は0より大きい数値で入力してください")
        return value


class PaymentResponse(BaseModel):
    id: int
    invoice_id: int
    payment_date: str
    amount: int
    remarks: str | None

    model_config = {"from_attributes": True}
