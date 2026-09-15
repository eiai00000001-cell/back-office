from pydantic import BaseModel, Field

from app.enums import ExpenseTaxCategory, PaymentMethod


class ExpenseCreateRequest(BaseModel):
    expense_date: str = Field(min_length=1, description="発生日を入力してください")
    account_category: str = Field(min_length=1, description="勘定科目を選択してください")
    amount: int = Field(gt=0, lt=10**10, description="金額は0より大きい数値で入力してください")
    tax_category: ExpenseTaxCategory = ExpenseTaxCategory.STANDARD_10
    payee: str | None = Field(default=None, max_length=100)
    payment_method: PaymentMethod | None = None
    memo: str | None = Field(default=None, max_length=500)


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
