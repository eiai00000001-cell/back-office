from datetime import date
from decimal import Decimal

import pytest

from app.enums import QuoteStatus, TaxCategory
from app.exceptions import NotFoundError, ValidationFailedError
from app.models.client import Client
from app.repositories.client_repository import ClientRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.quote_repository import QuoteRepository
from app.schemas.invoice import InvoiceItemInput
from app.schemas.quote import QuoteCreateRequest
from app.services.numbering_service import NumberingService
from app.services.quote_service import QuoteService
from app.repositories.project_repository import ProjectRepository
from app.services.tax_calculation_service import TaxCalculationService
from tests.conftest import now_iso


def _make_service(db_session):
    return QuoteService(
        QuoteRepository(db_session),
        ClientRepository(db_session),
        NumberingService(InvoiceRepository(db_session), QuoteRepository(db_session)),
        TaxCalculationService(),
        ProjectRepository(db_session),
    )


def _make_client(db_session) -> Client:
    client = Client(name="サンプル商事", created_at=now_iso(), updated_at=now_iso())
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


def _valid_dto(client_id: int, **overrides) -> QuoteCreateRequest:
    data = dict(
        client_id=client_id,
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
        remarks=None,
    )
    data.update(overrides)
    return QuoteCreateRequest(**data)


class TestCreateQuote:
    def test_creates_quote_with_calculated_totals_and_numbering(self, db_session):
        service = _make_service(db_session)
        client = _make_client(db_session)
        quote = service.create_quote(_valid_dto(client.id))
        year = date.today().year
        assert quote.quote_number == f"{year}-0001"
        assert quote.total_amount == 330000
        assert quote.status == "DRAFT"

    def test_raises_when_items_empty(self, db_session):
        service = _make_service(db_session)
        client = _make_client(db_session)
        with pytest.raises(ValidationFailedError):
            service.create_quote(_valid_dto(client.id, items=[]))

    def test_raises_when_issue_date_missing(self, db_session):
        service = _make_service(db_session)
        client = _make_client(db_session)
        with pytest.raises(ValidationFailedError):
            service.create_quote(_valid_dto(client.id, issue_date=None))

    def test_raises_when_expiry_date_missing(self, db_session):
        service = _make_service(db_session)
        client = _make_client(db_session)
        with pytest.raises(ValidationFailedError):
            service.create_quote(_valid_dto(client.id, expiry_date=None))


class TestUpdateQuoteStatus:
    def test_can_toggle_status_to_confirmed(self, db_session):
        service = _make_service(db_session)
        client = _make_client(db_session)
        quote = service.create_quote(_valid_dto(client.id))
        updated = service.update_quote(quote.id, _valid_dto(client.id, status=QuoteStatus.CONFIRMED))
        assert updated.status == "CONFIRMED"

    def test_raises_not_found_for_unknown_quote(self, db_session):
        service = _make_service(db_session)
        client = _make_client(db_session)
        with pytest.raises(NotFoundError):
            service.update_quote(9999, _valid_dto(client.id))


class TestListQuotes:
    def test_filters_by_status(self, db_session):
        service = _make_service(db_session)
        client = _make_client(db_session)
        service.create_quote(_valid_dto(client.id, status=QuoteStatus.DRAFT))
        service.create_quote(_valid_dto(client.id, status=QuoteStatus.CONFIRMED))
        confirmed = service.list_quotes(status="CONFIRMED")
        assert len(confirmed) == 1
        assert confirmed[0].status == "CONFIRMED"
