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

    def _period(self, today: date | None = None) -> tuple[str, str, list[str]]:
        # 詳細設計書4.8.1章: リクエストごとにサーバー実行時点のシステム日付を基準に算出する。
        today = today or date.today()
        month_keys = build_last_12_months(today)
        date_from = f"{month_keys[0]}-01"
        date_to = month_end(today)
        return date_from, date_to, month_keys

    @staticmethod
    def _fill_amount_by_month(
        rows: list[tuple[str, int]], month_keys: list[str]
    ) -> list[DashboardMonthlyAmountItem]:
        amounts = dict(rows)
        return [DashboardMonthlyAmountItem(month=m, amount=amounts.get(m, 0)) for m in month_keys]

    def get_sales_and_payments_summary(self, today: date | None = None) -> SalesAndPaymentsSummaryResponse:
        date_from, date_to, month_keys = self._period(today)
        sales_rows = self.invoice_repository.aggregate_total_by_issue_month(date_from, date_to)
        payment_rows = self.payment_repository.aggregate_amount_by_payment_month(date_from, date_to)
        return SalesAndPaymentsSummaryResponse(
            sales=self._fill_amount_by_month(sales_rows, month_keys),
            payments=self._fill_amount_by_month(payment_rows, month_keys),
        )

    def get_expense_summary(self, today: date | None = None) -> DashboardExpenseSummaryResponse:
        date_from, date_to, month_keys = self._period(today)
        monthly_rows = self.expense_repository.aggregate_by_month(date_from, date_to)
        category_rows = self.expense_repository.aggregate_by_category(date_from, date_to)
        # 円グラフ描画上、金額0円の科目は表示不要のため除外する(月次側の0円補完とは扱いが異なる。4.8.3章)。
        by_category = [
            CategorySummaryItem(account_category=category, count=count, total_amount=total)
            for category, count, total in category_rows
            if total != 0
        ]
        return DashboardExpenseSummaryResponse(
            monthly=self._fill_amount_by_month(monthly_rows, month_keys),
            by_category=by_category,
        )

    def get_profit_loss_summary(self, today: date | None = None) -> ProfitLossSummaryResponse:
        date_from, date_to, month_keys = self._period(today)
        sales_by_month = dict(self.invoice_repository.aggregate_total_by_issue_month(date_from, date_to))
        expense_by_month = dict(self.expense_repository.aggregate_by_month(date_from, date_to))
        monthly = [
            DashboardMonthlyAmountItem(month=m, amount=sales_by_month.get(m, 0) - expense_by_month.get(m, 0))
            for m in month_keys
        ]
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
