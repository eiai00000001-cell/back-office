"""レポート出力(F-10)。詳細設計書4.11章。サーバー側にファイルは保存せず、バイト列を返す。"""
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, UnprocessableError
from app.repositories.company_profile_repository import CompanyProfileRepository
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.report_repository import ReportRepository
from app.services.financial_aggregation_service import FinancialAggregationService
from app.services.payment_service import PaymentService
from app.services.pdf_generation_service import PdfGenerationService
from app.services.report_builders import (
    AccountingExportReport,
    ExpenseListReport,
    InvoiceListReport,
    MonthlyPlReport,
    PaymentListReport,
    ProjectSummaryReport,
    QuoteListReport,
    ReportBuilder,
)
from app.utils.csv_writer import CsvWriter

PERIOD_ORDER_MESSAGE = "開始年月は終了年月以前を指定してください"
CSV_ONLY_MESSAGE = "この種類はCSVのみ出力できます"
FORMAT_MESSAGE = "出力形式はcsvまたはpdfを指定してください"

REPORT_NAMES = {
    "invoices": "請求書一覧",
    "payments": "入金記録",
    "quotes": "見積書一覧",
    "expenses": "経費一覧",
    "monthly-pl": "月次損益集計レポート",
    "projects": "案件別サマリー",
    "accounting-export": "会計ソフト連携用エクスポート",
}
PDF_CAPABLE = {"monthly-pl"}


@dataclass
class ReportFile:
    content: bytes
    filename: str
    content_type: str
    record_count: int


class ReportService:
    def __init__(self, builders: dict[str, ReportBuilder], pdf_service: PdfGenerationService):
        self.builders = builders
        self.pdf_service = pdf_service

    def generate(self, report_type: str, date_from: str, date_to: str, fmt: str = "csv") -> ReportFile:
        builder = self.builders.get(report_type)
        if builder is None:
            raise NotFoundError(f"report type {report_type} not found")
        if fmt not in ("csv", "pdf"):
            raise UnprocessableError(FORMAT_MESSAGE)
        if fmt == "pdf" and report_type not in PDF_CAPABLE:
            raise UnprocessableError(CSV_ONLY_MESSAGE)
        if date.fromisoformat(date_from) > date.fromisoformat(date_to):
            raise UnprocessableError(PERIOD_ORDER_MESSAGE)

        data = builder.build(date_from, date_to)
        if fmt == "pdf":
            content = self.pdf_service.render_monthly_pl_report_pdf(data.monthly_pl)
            content_type = "application/pdf"
        else:
            content = CsvWriter.write(data.header, data.rows)
            content_type = "text/csv; charset=utf-8"
        period = f"{date_from[:4]}{date_from[5:7]}-{date_to[:4]}{date_to[5:7]}"
        return ReportFile(content, f"{REPORT_NAMES[report_type]}_{period}.{fmt}", content_type, data.record_count)


def build_report_service(session: Session, pdf_service: PdfGenerationService | None = None) -> ReportService:
    repository = ReportRepository(session)
    aggregation = FinancialAggregationService(
        InvoiceRepository(session), PaymentRepository(session), ExpenseRepository(session)
    )
    builders: dict[str, ReportBuilder] = {
        "invoices": InvoiceListReport(repository, PaymentService(PaymentRepository(session))),
        "payments": PaymentListReport(repository),
        "quotes": QuoteListReport(repository),
        "expenses": ExpenseListReport(repository),
        "monthly-pl": MonthlyPlReport(aggregation),
        "projects": ProjectSummaryReport(repository),
        "accounting-export": AccountingExportReport(repository),
    }
    return ReportService(builders, pdf_service or PdfGenerationService(CompanyProfileRepository(session)))
