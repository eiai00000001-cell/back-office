"""レポート種類別の内容作成(F-10)。詳細設計書4.11.2〜4.11.6章。

各Builderは build(date_from, date_to) -> ReportData を実装する。会計ソフト連携先の変更(★24。連携先は未定)は
AccountingExportReport内で完結する。
"""
from dataclasses import dataclass, field
from typing import Protocol

from app.enums import ACCOUNT_CATEGORIES
from app.repositories.report_repository import ReportRepository
from app.services.financial_aggregation_service import FinancialAggregationService
from app.services.payment_service import PaymentService
from app.utils.date_range import build_month_keys

PAYMENT_STATUS_LABELS = {"UNPAID": "未入金", "PARTIALLY_PAID": "一部入金", "PAID": "入金済み"}
QUOTE_STATUS_LABELS = {"DRAFT": "作成中", "CONFIRMED": "確定"}
EXPENSE_TAX_LABELS = {
    "STANDARD_10": "標準10%",
    "NON_TAXABLE": "非課税",
    "OUT_OF_SCOPE": "不課税",
    "NOT_APPLICABLE": "対象外",
}
PAYMENT_METHOD_LABELS = {"CASH": "現金", "CREDIT_CARD": "クレジットカード", "BANK_TRANSFER": "銀行振込", "OTHER": "その他"}
PROJECT_STATUS_LABELS = {"NOT_STARTED": "未着手", "IN_PROGRESS": "進行中", "WAITING_REVIEW": "確認待ち", "DONE": "完了"}


@dataclass
class MonthlyPlMonth:
    month: str
    sales: int
    expense_total: int
    profit: int
    category_expenses: dict[str, int] = field(default_factory=dict)


@dataclass
class MonthlyPlReportData:
    months: list[MonthlyPlMonth]
    total_sales: int
    total_expense: int
    total_profit: int
    category_totals: list[tuple[str, int]]


@dataclass
class ReportData:
    header: list[str]
    rows: list[list[object]]
    record_count: int
    monthly_pl: MonthlyPlReportData | None = None


class ReportBuilder(Protocol):
    def build(self, date_from: str, date_to: str) -> ReportData: ...


def _label(labels: dict[str, str], key: str | None) -> str:
    return labels.get(key, key) if key else ""


def _simple(header: list[str], rows: list[list[object]]) -> ReportData:
    return ReportData(header, rows, len(rows))


class InvoiceListReport:
    def __init__(self, repository: ReportRepository, payment_service: PaymentService):
        self.repository = repository
        self.payment_service = payment_service

    def build(self, date_from: str, date_to: str) -> ReportData:
        rows = [
            [
                i.invoice_number,
                i.client.name if i.client else "",
                i.project.name if i.project else "",
                i.issue_date,
                i.due_date,
                i.subtotal_amount,
                i.tax_amount,
                i.total_amount,
                PAYMENT_STATUS_LABELS[self.payment_service.calculate_status(i).value],
            ]
            for i in self.repository.invoices_in_period(date_from, date_to)
        ]
        return _simple(
            ["請求書番号", "取引先", "案件", "発行日", "支払期限", "小計", "消費税額", "合計", "入金ステータス"], rows
        )


class PaymentListReport:
    def __init__(self, repository: ReportRepository):
        self.repository = repository

    def build(self, date_from: str, date_to: str) -> ReportData:
        rows = [
            [number, p.payment_date, p.amount, p.remarks]
            for p, number in self.repository.payments_in_period(date_from, date_to)
        ]
        return _simple(["請求書番号", "入金日", "入金額", "備考"], rows)


class QuoteListReport:
    def __init__(self, repository: ReportRepository):
        self.repository = repository

    def build(self, date_from: str, date_to: str) -> ReportData:
        rows = [
            [
                q.quote_number,
                q.client.name if q.client else "",
                q.project.name if q.project else "",
                q.issue_date,
                q.expiry_date,
                q.total_amount,
                _label(QUOTE_STATUS_LABELS, q.status),
            ]
            for q in self.repository.quotes_in_period(date_from, date_to)
        ]
        return _simple(["見積書番号", "取引先", "案件", "発行日", "有効期限", "合計", "ステータス"], rows)


class ExpenseListReport:
    def __init__(self, repository: ReportRepository):
        self.repository = repository

    def build(self, date_from: str, date_to: str) -> ReportData:
        rows = [
            [
                e.expense_date,
                e.account_category,
                e.amount,
                _label(EXPENSE_TAX_LABELS, e.tax_category),
                e.payee,
                _label(PAYMENT_METHOD_LABELS, e.payment_method),
                e.memo,
            ]
            for e in self.repository.expenses_in_period(date_from, date_to)
        ]
        return _simple(["発生日", "勘定科目", "金額", "税区分", "支払先", "支払方法", "メモ"], rows)


class ProjectSummaryReport:
    def __init__(self, repository: ReportRepository):
        self.repository = repository

    def build(self, date_from: str, date_to: str) -> ReportData:
        rows = [
            [
                r.name,
                r.client_name,
                _label(PROJECT_STATUS_LABELS, r.status),
                r.due_date,
                r.quote_count,
                r.quote_amount,
                r.invoice_count,
                r.invoice_amount,
            ]
            for r in self.repository.project_summaries(date_from, date_to)
        ]
        return _simple(["案件名", "取引先", "ステータス", "納期", "見積件数", "見積金額", "請求件数", "請求金額"], rows)


class AccountingExportReport:
    """会計ソフト連携用の汎用明細CSV(★24。連携先は未定。詳細設計書4.11.6)。"""

    SALES, EXPENSE = 0, 1

    def __init__(self, repository: ReportRepository):
        self.repository = repository

    def build(self, date_from: str, date_to: str) -> ReportData:
        entries: list[tuple[tuple, list[object]]] = []
        for i in self.repository.invoices_in_period(date_from, date_to):
            memo = i.invoice_number + (f" / {i.project.name}" if i.project else "")
            entries.append((
                (i.issue_date, self.SALES, i.invoice_number, i.id),
                ["売上", i.issue_date, "売上高", i.client.name if i.client else "", memo,
                 i.total_amount, i.tax_amount, "", i.invoice_number],
            ))
        for e in self.repository.expenses_in_period(date_from, date_to):
            entries.append((
                (e.expense_date, self.EXPENSE, "", e.id),
                ["経費", e.expense_date, e.account_category, e.payee, e.memo, e.amount, "",
                 _label(EXPENSE_TAX_LABELS, e.tax_category), ""],
            ))
        entries.sort(key=lambda entry: entry[0])
        rows = [row for _key, row in entries]
        header = ["区分", "日付", "勘定科目", "取引先・支払先", "摘要", "金額", "うち消費税額", "税区分", "書類番号"]
        return _simple(header, rows)


def _category_sort_key(category: str) -> tuple[int, str]:
    order = ACCOUNT_CATEGORIES.index(category) if category in ACCOUNT_CATEGORIES else len(ACCOUNT_CATEGORIES)
    return order, category


class MonthlyPlReport:
    """月次損益集計レポート(縦持ちCSV/PDF用データ)。集計はF-07と共通のFinancialAggregationService。"""

    def __init__(self, aggregation: FinancialAggregationService):
        self.aggregation = aggregation

    def build(self, date_from: str, date_to: str) -> ReportData:
        month_keys = build_month_keys(date_from, date_to)
        sales = self.aggregation.monthly_sales(date_from, date_to)
        expenses = self.aggregation.monthly_expenses(date_from, date_to)
        by_category = self.aggregation.monthly_expenses_by_category(date_from, date_to)
        profit = self.aggregation.monthly_profit_loss(date_from, date_to)

        months: list[MonthlyPlMonth] = []
        rows: list[list[object]] = []
        category_totals: dict[str, int] = {}
        record_count = 0
        for m in month_keys:
            month_sales = sales.get(m, 0)
            month_expense = expenses.get(m, 0)
            month_categories = dict(sorted(by_category.get(m, {}).items(), key=lambda kv: _category_sort_key(kv[0])))
            month_profit = profit.get(m, 0)
            months.append(MonthlyPlMonth(m, month_sales, month_expense, month_profit, month_categories))
            if month_sales != 0 or month_expense != 0:
                record_count += 1
            rows.append([m, "売上", "", month_sales])
            for category, amount in month_categories.items():
                rows.append([m, "経費", category, amount])
                category_totals[category] = category_totals.get(category, 0) + amount
            rows.append([m, "経費合計", "", month_expense])
            rows.append([m, "損益", "", month_profit])

        data = MonthlyPlReportData(
            months=months,
            total_sales=sum(x.sales for x in months),
            total_expense=sum(x.expense_total for x in months),
            total_profit=sum(x.profit for x in months),
            category_totals=sorted(category_totals.items(), key=lambda kv: _category_sort_key(kv[0])),
        )
        return ReportData(["年月", "区分", "勘定科目", "金額"], rows, record_count, monthly_pl=data)
