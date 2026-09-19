from datetime import date
from decimal import Decimal

import pytest

from app.enums import TaxCategory
from app.exceptions import NotFoundError, ValidationFailedError
from app.models.client import Client
from app.repositories.client_repository import ClientRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.quote_repository import QuoteRepository
from app.schemas.invoice import InvoiceCreateRequest, InvoiceItemInput, InvoiceUpdateRequest
from app.services.invoice_service import InvoiceService
from app.services.numbering_service import NumberingService
from app.repositories.project_repository import ProjectRepository
from app.services.tax_calculation_service import TaxCalculationService
from tests.conftest import now_iso


def _make_service(db_session):
    return InvoiceService(
        InvoiceRepository(db_session),
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


def _valid_dto(client_id: int, **overrides) -> InvoiceCreateRequest:
    data = dict(
        client_id=client_id,
        issue_date="2026-08-01",
        due_date="2026-08-31",
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
    return InvoiceCreateRequest(**data)


class TestCreateInvoice:
    def test_creates_invoice_with_calculated_totals_and_numbering(self, db_session):
        service = _make_service(db_session)
        client = _make_client(db_session)
        invoice = service.create_invoice(_valid_dto(client.id))
        year = date.today().year
        assert invoice.invoice_number == f"{year}-0001"
        assert invoice.subtotal_amount == 300000
        assert invoice.tax_amount == 30000
        assert invoice.total_amount == 330000
        assert len(invoice.items) == 1

    def test_raises_when_items_empty(self, db_session):
        service = _make_service(db_session)
        client = _make_client(db_session)
        with pytest.raises(ValidationFailedError):
            service.create_invoice(_valid_dto(client.id, items=[]))

    def test_raises_when_issue_date_missing(self, db_session):
        service = _make_service(db_session)
        client = _make_client(db_session)
        with pytest.raises(ValidationFailedError):
            service.create_invoice(_valid_dto(client.id, issue_date=None))

    def test_raises_when_due_date_missing(self, db_session):
        service = _make_service(db_session)
        client = _make_client(db_session)
        with pytest.raises(ValidationFailedError):
            service.create_invoice(_valid_dto(client.id, due_date=None))

    def test_raises_when_client_does_not_exist(self, db_session):
        service = _make_service(db_session)
        with pytest.raises(ValidationFailedError):
            service.create_invoice(_valid_dto(client_id=9999))

    def test_second_invoice_gets_next_sequence_number(self, db_session):
        service = _make_service(db_session)
        client = _make_client(db_session)
        service.create_invoice(_valid_dto(client.id))
        second = service.create_invoice(_valid_dto(client.id))
        year = date.today().year
        assert second.invoice_number == f"{year}-0002"


class TestUpdateInvoice:
    def test_update_replaces_items_and_recalculates_totals(self, db_session):
        service = _make_service(db_session)
        client = _make_client(db_session)
        invoice = service.create_invoice(_valid_dto(client.id))
        updated = service.update_invoice(
            invoice.id,
            _valid_dto(
                client.id,
                items=[
                    InvoiceItemInput(
                        item_name="別の品目",
                        quantity=Decimal("2"),
                        unit_price=1000,
                        tax_category=TaxCategory.NON_TAXABLE,
                    )
                ],
            ),
        )
        assert updated.total_amount == 2000
        assert len(updated.items) == 1
        assert updated.items[0].item_name == "別の品目"

    def test_raises_not_found_for_unknown_invoice(self, db_session):
        service = _make_service(db_session)
        client = _make_client(db_session)
        with pytest.raises(NotFoundError):
            service.update_invoice(9999, _valid_dto(client.id))


class TestListAndDeleteInvoice:
    def test_list_invoices_returns_created_invoices(self, db_session):
        service = _make_service(db_session)
        client = _make_client(db_session)
        service.create_invoice(_valid_dto(client.id))
        invoices = service.list_invoices()
        assert len(invoices) == 1

    def test_delete_invoice_removes_it(self, db_session):
        service = _make_service(db_session)
        client = _make_client(db_session)
        invoice = service.create_invoice(_valid_dto(client.id))
        service.delete_invoice(invoice.id)
        assert service.list_invoices() == []
