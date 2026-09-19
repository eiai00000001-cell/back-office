"""財務ダッシュボード(F-07、イテレーション2)。詳細設計書4.8章。

新規テーブルは持たず、既存の請求書・経費・見積書・入金データを読み取り集計するのみの
読み取り専用サービス。書き込み処理は一切行わない。
"""
from datetime import date

from app.repositories.expense_repository import ExpenseRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.quote_repository import QuoteRepository
from app.schemas.dashboard import (
    DashboardExpenseSummaryResponse,
    DashboardMonthlyAmountItem,
    ProfitLossSummaryResponse,
    QuoteMonthlySummaryItem,
    QuoteStatusSummaryResponse,
    SalesAndPaymentsSummaryResponse,
)
from app.schemas.expense import CategorySummaryItem
from app.services.financial_aggregation_service import FinancialAggregationService
from app.utils.date_range import build_last_12_months, month_end


class DashboardService:
    def __init__(
        self,
        invoice_repository: InvoiceRepository,
        payment_repository: PaymentRepository,
        expense_repository: ExpenseRepository,
        quote_repository: QuoteRepository,
    ):
        self.invoice_repository = invoice_repository
        self.payment_repository = payment_repository
        self.expense_repository = expense_repository
        self.quote_repository = quote_repository
        # 集計はF-10・F-11と共通のサービスへ委譲する(詳細設計書4.12.1)
        self.aggregation = FinancialAggregationService(invoice_repository, payment_repository, expense_repository)

    def _period(self, today: date | None = None) -> tuple[str, str, list[str]]:
        # 詳細設計書4.8.1章: リクエストごとにサーバー実行時点のシステム日付を基準に算出する。
        today = today or date.today()
        month_keys = build_last_12_months(today)
        date_from = f"{month_keys[0]}-01"
        date_to = month_end(today)
        return date_from, date_to, month_keys

    @staticmethod
    def _fill_amount_by_month(
        amounts: dict[str, int], month_keys: list[str]
    ) -> list[DashboardMonthlyAmountItem]:
        return [DashboardMonthlyAmountItem(month=m, amount=amounts.get(m, 0)) for m in month_keys]

    def get_sales_and_payments_summary(self, today: date | None = None) -> SalesAndPaymentsSummaryResponse:
        date_from, date_to, month_keys = self._period(today)
        return SalesAndPaymentsSummaryResponse(
            sales=self._fill_amount_by_month(self.aggregation.monthly_sales(date_from, date_to), month_keys),
            payments=self._fill_amount_by_month(self.aggregation.monthly_payments(date_from, date_to), month_keys),
        )

    def get_expense_summary(self, today: date | None = None) -> DashboardExpenseSummaryResponse:
        date_from, date_to, month_keys = self._period(today)
        monthly_amounts = self.aggregation.monthly_expenses(date_from, date_to)
        category_rows = self.aggregation.expense_category_rows(date_from, date_to)
        # 円グラフ描画上、金額0円の科目は表示不要のため除外する(月次側の0円補完とは扱いが異なる。4.8.3章)。
        by_category = [
            CategorySummaryItem(account_category=category, count=count, total_amount=total)
            for category, count, total in category_rows
            if total != 0
        ]
        return DashboardExpenseSummaryResponse(
            monthly=self._fill_amount_by_month(monthly_amounts, month_keys),
            by_category=by_category,
        )

    def get_profit_loss_summary(self, today: date | None = None) -> ProfitLossSummaryResponse:
        date_from, date_to, month_keys = self._period(today)
        profit_by_month = self.aggregation.monthly_profit_loss(date_from, date_to)
        monthly = [DashboardMonthlyAmountItem(month=m, amount=profit_by_month.get(m, 0)) for m in month_keys]
        return ProfitLossSummaryResponse(monthly=monthly)

    def get_quote_status_summary(self, today: date | None = None) -> QuoteStatusSummaryResponse:
        date_from, date_to, month_keys = self._period(today)
        rows_by_month = {
            month: (count, total_amount)
            for month, count, total_amount in self.quote_repository.aggregate_count_and_amount_by_issue_month(
                date_from, date_to
            )
        }
        monthly = [
            QuoteMonthlySummaryItem(
                month=m,
                count=rows_by_month.get(m, (0, 0))[0],
                total_amount=rows_by_month.get(m, (0, 0))[1],
            )
            for m in month_keys
        ]

        total_count = self.quote_repository.count_in_period(date_from, date_to)
        converted_count = self.quote_repository.count_converted_in_period(date_from, date_to)
        # 0除算回避(4.8.5章): 対象見積件数が0の場合はnullを返し、フロントエンドが「-」等を表示する。
        conversion_rate = None if total_count == 0 else converted_count / total_count

        return QuoteStatusSummaryResponse(monthly=monthly, conversion_rate=conversion_rate)
