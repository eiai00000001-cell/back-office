from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field, field_validator

from app.enums import ExpenseTaxCategory, PaymentMethod


class ExpenseCreateRequest(BaseModel):
    expense_date: str = Field(min_length=1, description="発生日を入力してください")
    account_category: str = Field(min_length=1, description="勘定科目を選択してください")
    amount: int = Field(gt=0, lt=10**10, description="金額は0より大きい数値で入力してください")
    tax_category: ExpenseTaxCategory = ExpenseTaxCategory.STANDARD_10
    payee: str | None = Field(default=None, max_length=100)
    payment_method: PaymentMethod | None = None
    memo: str | None = Field(default=None, max_length=500)
    project_id: int | None = None

    # レビュー指摘1対応: Field(description=...)は実際のエラーメッセージにならないため、
    # mode="before"バリデータで詳細設計書3.6章の日本語メッセージを明示的に返す。
    @field_validator("expense_date", mode="before")
    @classmethod
    def validate_expense_date_presence(cls, value: object) -> object:
        if not isinstance(value, str) or value.strip() == "":
            raise ValueError("発生日を入力してください")
        return value

    @field_validator("account_category", mode="before")
    @classmethod
    def validate_account_category_presence(cls, value: object) -> object:
        if not isinstance(value, str) or value.strip() == "":
            raise ValueError("勘定科目を選択してください")
        return value

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount_positive(cls, value: object) -> object:
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("金額は0より大きい数値で入力してください") from exc
        if decimal_value <= 0 or decimal_value >= 10**10:
            raise ValueError("金額は0より大きい数値で入力してください")
        return value


class ExpenseUpdateRequest(ExpenseCreateRequest):
    pass


class ExpenseResponse(BaseModel):
    id: int
    expense_date: str
    account_category: str
    amount: int
    tax_category: ExpenseTaxCategory
    payee: str | None
    payment_method: PaymentMethod | None
    memo: str | None
    attachment_path: str | None
    attachment_original_name: str | None
    project_id: int | None = None
    project_name: str | None = None

    model_config = {"from_attributes": True}


class CategorySummaryItem(BaseModel):
    account_category: str
    count: int
    total_amount: int


class MonthSummaryItem(BaseModel):
    year_month: str
    total_amount: int


class ExpenseSummaryResponse(BaseModel):
    by_category: list[CategorySummaryItem]
    by_month: list[MonthSummaryItem]
