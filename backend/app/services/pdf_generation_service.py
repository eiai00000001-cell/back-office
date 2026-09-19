"""請求書・見積書・月次損益集計レポートPDF生成。詳細設計書4.1ステップ10・4.3ステップ4・4.11.5。"""
from datetime import date

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from app.config import APP_DIR
from app.enums import TaxCategory
from app.repositories.company_profile_repository import CompanyProfileRepository

TAX_CATEGORY_LABELS = {
    TaxCategory.STANDARD_10.value: "標準10%",
    TaxCategory.NON_TAXABLE.value: "非課税",
    TaxCategory.OUT_OF_SCOPE.value: "不課税",
}

TAX_SUBTOTAL_LABELS = {
    TaxCategory.STANDARD_10.value: "小計(標準10%)",
    TaxCategory.NON_TAXABLE.value: "小計(非課税)",
    TaxCategory.OUT_OF_SCOPE.value: "小計(不課税)",
}

_env = Environment(
    loader=FileSystemLoader(str(APP_DIR / "templates")),
    autoescape=select_autoescape(["html"]),
)


class PdfGenerationService:
    def __init__(self, company_profile_repository: CompanyProfileRepository):
        self.company_profile_repository = company_profile_repository

    def _render(self, document_title: str, document_number: str, entity, date_fields: list[tuple[str, object]]) -> bytes:
        profile = self.company_profile_repository.get()
        items = list(entity.items)
        subtotal_by_tax: dict[str, int] = {}
        for item in items:
            subtotal_by_tax[item.tax_category] = subtotal_by_tax.get(item.tax_category, 0) + item.amount

        tax_breakdown: list[tuple[str, int]] = []
        for category in (TaxCategory.STANDARD_10.value, TaxCategory.NON_TAXABLE.value, TaxCategory.OUT_OF_SCOPE.value):
            if category in subtotal_by_tax:
                tax_breakdown.append((TAX_SUBTOTAL_LABELS[category], subtotal_by_tax[category]))
        if TaxCategory.STANDARD_10.value in subtotal_by_tax:
            tax_breakdown.append(("消費税額(標準10%)", entity.tax_amount))

        template = _env.get_template("pdf_base.html")
        html_content = template.render(
            document_title=document_title,
            document_number=document_number,
            client_name=entity.client.name if entity.client else "",
            client_address=entity.client.address if entity.client else "",
            issuer_name=profile.name if profile else "",
            issuer_business_name=profile.business_name if profile else "",
            issuer_address=profile.address if profile else "",
            issuer_contact_info=profile.contact_info if profile else "",
            issuer_registration_number=profile.invoice_registration_number if profile else "",
            date_fields=date_fields,
            items=[
                {
                    "item_name": item.item_name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "tax_category_label": TAX_CATEGORY_LABELS.get(item.tax_category, item.tax_category),
                    "amount": item.amount,
                }
                for item in items
            ],
            tax_breakdown=tax_breakdown,
            total_amount=entity.total_amount,
            remarks=entity.remarks,
        )
        return HTML(string=html_content).write_pdf()

    def render_invoice_pdf(self, invoice) -> bytes:
        return self._render(
            "請求書",
            invoice.invoice_number,
            invoice,
            [("発行日", invoice.issue_date), ("支払期限", invoice.due_date)],
        )

    def render_quote_pdf(self, quote) -> bytes:
        return self._render(
            "見積書",
            quote.quote_number,
            quote,
            [("発行日", quote.issue_date), ("有効期限", quote.expiry_date)],
        )

    def render_monthly_pl_report_pdf(self, report) -> bytes:
        """月次損益集計レポート(F-10、詳細設計書4.11.5)。report は report_builders.MonthlyPlReportData。"""
        profile = self.company_profile_repository.get()
        issuer_name = ""
        if profile:
            issuer_name = profile.business_name or profile.name or ""
        first, last = report.months[0].month, report.months[-1].month
        template = _env.get_template("monthly_pl_report.html")
        html_content = template.render(
            period_label=f"{first} 〜 {last}",
            issuer_name=issuer_name,
            created_on=date.today().isoformat(),
            months=report.months,
            total_sales=report.total_sales,
            total_expense=report.total_expense,
            total_profit=report.total_profit,
            category_totals=report.category_totals,
        )
        return HTML(string=html_content).write_pdf()
