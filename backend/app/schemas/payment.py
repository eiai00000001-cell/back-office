from pydantic import BaseModel, Field


class PaymentCreateRequest(BaseModel):
    payment_date: str
    amount: int = Field(gt=0, description="入金額は0より大きい数値で入力してください")
    remarks: str | None = Field(default=None, max_length=200)
    force: bool = Field(default=False, description="入金額合計が請求金額を超過する場合の確認済みフラグ")


class PaymentResponse(BaseModel):
    id: int
    invoice_id: int
    payment_date: str
    amount: int
    remarks: str | None

    model_config = {"from_attributes": True}
