from datetime import date
from decimal import Decimal

import pytest

from app.enums import QuoteStatus, TaxCategory
from app.exceptions import ConflictError, NotFoundError
from app.models.client import Client
from app.repositories.client_repository import ClientRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.quote_repository import QuoteRepository
from app.schemas.invoice import InvoiceItemInput
from app.schemas.quote import QuoteCreateRequest
from app.services.numbering_service import NumberingService
from app.services.quote_service import QuoteService
from app.services.quote_to_invoice_conversion_service import QuoteToInvoiceConversionService
from app.repositories.project_repository import ProjectRepository
from app.services.tax_calculation_service import TaxCalculationService
from tests.conftest import now_iso


def _make_client(db_session) -> Client:
    client = Client(name="サンプル商事", created_at=now_iso(), updated_at=now_iso())
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


def _make_quote_service(db_session):
    return QuoteService(
        QuoteRepository(db_session),
        ClientRepository(db_session),
        NumberingService(InvoiceRepository(db_session), QuoteRepository(db_session)),
        TaxCalculationService(),
        ProjectRepository(db_session),
    )


def _make_conversion_service(db_session):
    return QuoteToInvoiceConversionService(
        QuoteRepository(db_session),
        InvoiceRepository(db_session),
        NumberingService(InvoiceRepository(db_session), QuoteRepository(db_session)),
    )


class TestConvert:
    def test_creates_invoice_with_null_dates_and_copied_items(self, db_session):
        client = _make_client(db_session)
        quote_service = _make_quote_service(db_session)
        quote = quote_service.create_quote(
            QuoteCreateRequest(
                client_id=client.id,
                issue_date="2026-07-25",
                expiry_date="2026-08-25",
                status=QuoteStatus.DRAFT,
                items=[
                    InvoiceItemInput(
                        item_name="Webサイト制作作業",
                        quantity=Decimal("1"),
                        unit_price=300000,
                        tax_category=TaxCategory.STANDARD_10,
                    )
                ],
            )
        )
        conversion_service = _make_conversion_service(db_session)
        invoice = conversion_service.convert(quote.id)

        assert invoice.source_quote_id == quote.id
        assert invoice.issue_date is None
        assert invoice.due_date is None
        assert invoice.client_id == client.id
        assert invoice.total_amount == 330000
        assert len(invoice.items) == 1
        assert invoice.items[0].item_name == "Webサイト制作作業"
        year = date.today().year
        assert invoice.invoice_number == f"{year}-0001"

    def test_allows_conversion_of_draft_status_quote(self, db_session):
        client = _make_client(db_session)
        quote_service = _make_quote_service(db_session)
        quote = quote_service.create_quote(
            QuoteCreateRequest(
                client_id=client.id,
                issue_date="2026-07-25",
                expiry_date="2026-08-25",
                status=QuoteStatus.DRAFT,
                items=[
                    InvoiceItemInput(
                        item_name="A", quantity=Decimal("1"), unit_price=1000, tax_category=TaxCategory.STANDARD_10
                    )
                ],
            )
        )
        conversion_service = _make_conversion_service(db_session)
        invoice = conversion_service.convert(quote.id)
        assert invoice is not None

    def test_raises_conflict_when_already_converted(self, db_session):
        client = _make_client(db_session)
        quote_service = _make_quote_service(db_session)
        quote = quote_service.create_quote(
            QuoteCreateRequest(
                client_id=client.id,
                issue_date="2026-07-25",
                expiry_date="2026-08-25",
                status=QuoteStatus.DRAFT,
                items=[
                    InvoiceItemInput(
                        item_name="A", quantity=Decimal("1"), unit_price=1000, tax_category=TaxCategory.STANDARD_10
                    )
                ],
            )
        )
        conversion_service = _make_conversion_service(db_session)
        conversion_service.convert(quote.id)
        with pytest.raises(ConflictError):
            conversion_service.convert(quote.id)

    def test_raises_not_found_for_unknown_quote(self, db_session):
        conversion_service = _make_conversion_service(db_session)
        with pytest.raises(NotFoundError):
            conversion_service.convert(9999)

    def test_editing_converted_invoice_does_not_affect_source_quote(self, db_session):
        client = _make_client(db_session)
        quote_service = _make_quote_service(db_session)
        quote = quote_service.create_quote(
            QuoteCreateRequest(
                client_id=client.id,
                issue_date="2026-07-25",
                expiry_date="2026-08-25",
                status=QuoteStatus.DRAFT,
                items=[
                    InvoiceItemInput(
                        item_name="A", quantity=Decimal("1"), unit_price=1000, tax_category=TaxCategory.STANDARD_10
                    )
                ],
            )
        )
        conversion_service = _make_conversion_service(db_session)
        invoice = conversion_service.convert(quote.id)
        invoice.remarks = "編集済み"
        db_session.commit()

        refreshed_quote = quote_service.get_quote(quote.id)
        assert refreshed_quote.remarks is None
