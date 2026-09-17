"""財務ダッシュボード(F-07、イテレーション2)向けレスポンススキーマ。詳細設計書5.5章。

読み取り専用機能のためリクエストスキーマは持たない。
"""
from pydantic import BaseModel

from app.schemas.expense import CategorySummaryItem


class DashboardMonthlyAmountItem(BaseModel):
    month: str
    amount: int


class QuoteMonthlySummaryItem(BaseModel):
    month: str
    count: int
    total_amount: int


class SalesAndPaymentsSummaryResponse(BaseModel):
    sales: list[DashboardMonthlyAmountItem]
    payments: list[DashboardMonthlyAmountItem]


class DashboardExpenseSummaryResponse(BaseModel):
    monthly: list[DashboardMonthlyAmountItem]
    by_category: list[CategorySummaryItem]


class ProfitLossSummaryResponse(BaseModel):
    monthly: list[DashboardMonthlyAmountItem]


class QuoteStatusSummaryResponse(BaseModel):
    monthly: list[QuoteMonthlySummaryItem]
    conversion_rate: float | None
