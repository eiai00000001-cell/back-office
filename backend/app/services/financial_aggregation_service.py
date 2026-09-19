"""月次の売上・入金・経費・損益の共通集計(F-07・F-10・F-11で共用)。詳細設計書4.12.1章。

集計定義(発生主義。売上=請求書の発行日、経費=経費の発生日、勘定科目区分=F-02)をここに一元化する。
読み取り専用。0円補完は呼び出し側が月一覧に対して行う。
"""
from collections import defaultdict

from app.repositories.expense_repository import ExpenseRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository


class FinancialAggregationService:
    def __init__(
        self,
        invoice_repository: InvoiceRepository,
        payment_repository: PaymentRepository,
        expense_repository: ExpenseRepository,
    ):
        self.invoice_repository = invoice_repository
        self.payment_repository = payment_repository
        self.expense_repository = expense_repository

    def monthly_sales(self, date_from: str, date_to: str) -> dict[str, int]:
        return dict(self.invoice_repository.aggregate_total_by_issue_month(date_from, date_to))

    def monthly_payments(self, date_from: str, date_to: str) -> dict[str, int]:
        return dict(self.payment_repository.aggregate_amount_by_payment_month(date_from, date_to))

    def monthly_expenses(self, date_from: str, date_to: str) -> dict[str, int]:
        return dict(self.expense_repository.aggregate_by_month(date_from, date_to))

    def expense_category_rows(self, date_from: str, date_to: str) -> list[tuple[str, int, int]]:
        """勘定科目別の(科目, 件数, 合計)。F-07の内訳が件数を含むため、辞書版とは別に公開する。"""
        return self.expense_repository.aggregate_by_category(date_from, date_to)

    def expense_by_category(self, date_from: str, date_to: str) -> dict[str, int]:
        return {category: total for category, _count, total in self.expense_category_rows(date_from, date_to)}

    def monthly_expenses_by_category(self, date_from: str, date_to: str) -> dict[str, dict[str, int]]:
        result: dict[str, dict[str, int]] = defaultdict(dict)
        for month, category, total in self.expense_repository.aggregate_by_month_and_category(date_from, date_to):
            result[month][category] = total
        return dict(result)

    def monthly_profit_loss(self, date_from: str, date_to: str) -> dict[str, int]:
        """月次損益=売上-経費(負の値あり)。売上・経費のいずれかがある月を返す。"""
        sales = self.monthly_sales(date_from, date_to)
        expenses = self.monthly_expenses(date_from, date_to)
        return {m: sales.get(m, 0) - expenses.get(m, 0) for m in sorted(set(sales) | set(expenses))}
