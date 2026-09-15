from decimal import Decimal

from app.enums import TaxCategory
from app.models.client import Client
from app.models.company_profile import CompanyProfile
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.repositories.company_profile_repository import CompanyProfileRepository
from app.services.pdf_generation_service import PdfGenerationService
from tests.conftest import now_iso


def _make_client(db_session) -> Client:
    client = Client(name="株式会社サンプル商事", address="東京都千代田区1-1-1", created_at=now_iso(), updated_at=now_iso())
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


class TestRenderInvoicePdf:
    def test_generates_pdf_bytes(self, db_session):
        client = _make_client(db_session)
        invoice = Invoice(
            invoice_number="2026-0001",
            client_id=client.id,
            client=client,
            issue_date="2026-08-01",
            due_date="2026-08-31",
            subtotal_amount=300000,
            tax_amount=30000,
            total_amount=330000,
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        invoice.items = [
            InvoiceItem(
                item_name="Webサイト制作作業",
                quantity=Decimal("1"),
                unit_price=300000,
                tax_category=TaxCategory.STANDARD_10.value,
                amount=300000,
                sort_order=0,
            )
        ]
        db_session.add(invoice)
        db_session.commit()

        service = PdfGenerationService(CompanyProfileRepository(db_session))
        pdf_bytes = service.render_invoice_pdf(invoice)
        assert pdf_bytes.startswith(b"%PDF")

    def test_generates_pdf_with_registration_number_when_set(self, db_session):
        client = _make_client(db_session)
        db_session.add(
            CompanyProfile(id=1, name="山田太郎", invoice_registration_number="T1234567890123", updated_at=now_iso())
        )
        invoice = Invoice(
            invoice_number="2026-0002",
            client_id=client.id,
            client=client,
            subtotal_amount=1000,
            tax_amount=100,
            total_amount=1100,
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        invoice.items = [
            InvoiceItem(
                item_name="品目",
                quantity=Decimal("1"),
                unit_price=1000,
                tax_category=TaxCategory.STANDARD_10.value,
                amount=1000,
                sort_order=0,
            )
        ]
        db_session.add(invoice)
        db_session.commit()

        service = PdfGenerationService(CompanyProfileRepository(db_session))
        pdf_bytes = service.render_invoice_pdf(invoice)
        assert pdf_bytes.startswith(b"%PDF")


class TestRenderQuotePdf:
    def test_generates_pdf_bytes(self, db_session):
        client = _make_client(db_session)
        quote = Quote(
            quote_number="2026-0001",
            client_id=client.id,
            client=client,
            issue_date="2026-07-25",
            expiry_date="2026-08-25",
            status="DRAFT",
            subtotal_amount=300000,
            tax_amount=30000,
            total_amount=330000,
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        quote.items = [
            QuoteItem(
                item_name="Webサイト制作作業",
                quantity=Decimal("1"),
                unit_price=300000,
                tax_category=TaxCategory.STANDARD_10.value,
                amount=300000,
                sort_order=0,
            )
        ]
        db_session.add(quote)
        db_session.commit()

        service = PdfGenerationService(CompanyProfileRepository(db_session))
        pdf_bytes = service.render_quote_pdf(quote)
        assert pdf_bytes.startswith(b"%PDF")
