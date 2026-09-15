from datetime import date

from app.models.client import Client
from app.models.invoice import Invoice
from app.models.quote import Quote
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.quote_repository import QuoteRepository
from app.services.numbering_service import NumberingService
from tests.conftest import now_iso


def _make_client(db_session) -> Client:
    client = Client(name="サンプル商事", created_at=now_iso(), updated_at=now_iso())
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


class TestGenerateNumberInvoice:
    def test_first_invoice_number_of_the_year_is_0001(self, db_session):
        service = NumberingService(InvoiceRepository(db_session), QuoteRepository(db_session))
        year = date.today().year
        number = service.generate_number("invoice")
        assert number == f"{year}-0001"

    def test_increments_sequence_based_on_existing_max(self, db_session):
        client = _make_client(db_session)
        year = date.today().year
        db_session.add(
            Invoice(
                invoice_number=f"{year}-0003",
                client_id=client.id,
                created_at=now_iso(),
                updated_at=now_iso(),
            )
        )
        db_session.commit()
        service = NumberingService(InvoiceRepository(db_session), QuoteRepository(db_session))
        assert service.generate_number("invoice") == f"{year}-0004"

    def test_ignores_other_years_when_computing_sequence(self, db_session):
        client = _make_client(db_session)
        db_session.add(
            Invoice(
                invoice_number="2000-0099",
                client_id=client.id,
                created_at=now_iso(),
                updated_at=now_iso(),
            )
        )
        db_session.commit()
        service = NumberingService(InvoiceRepository(db_session), QuoteRepository(db_session))
        year = date.today().year
        assert service.generate_number("invoice") == f"{year}-0001"


class TestGenerateNumberQuote:
    def test_quote_and_invoice_counters_are_independent(self, db_session):
        client = _make_client(db_session)
        year = date.today().year
        db_session.add(
            Invoice(
                invoice_number=f"{year}-0005",
                client_id=client.id,
                created_at=now_iso(),
                updated_at=now_iso(),
            )
        )
        db_session.add(
            Quote(
                quote_number=f"{year}-0001",
                client_id=client.id,
                status="DRAFT",
                created_at=now_iso(),
                updated_at=now_iso(),
            )
        )
        db_session.commit()
        service = NumberingService(InvoiceRepository(db_session), QuoteRepository(db_session))
        assert service.generate_number("quote") == f"{year}-0002"
        assert service.generate_number("invoice") == f"{year}-0006"
