from app.repositories.company_profile_repository import CompanyProfileRepository
from app.schemas.company_profile import CompanyProfileUpdateRequest
from app.services.company_profile_service import CompanyProfileService


class TestCompanyProfileService:
    def test_get_profile_returns_default_empty_profile_when_unset(self, db_session):
        service = CompanyProfileService(CompanyProfileRepository(db_session))
        profile = service.get_profile()
        assert profile.name == ""
        assert profile.invoice_registration_number is None

    def test_update_profile_persists_values(self, db_session):
        service = CompanyProfileService(CompanyProfileRepository(db_session))
        dto = CompanyProfileUpdateRequest(
            name="山田 太郎",
            business_name="EIAI TEC",
            invoice_registration_number="T1234567890123",
        )
        updated = service.update_profile(dto)
        assert updated.name == "山田 太郎"
        assert updated.invoice_registration_number == "T1234567890123"

        fetched = service.get_profile()
        assert fetched.name == "山田 太郎"

    def test_update_profile_allows_empty_registration_number(self, db_session):
        service = CompanyProfileService(CompanyProfileRepository(db_session))
        dto = CompanyProfileUpdateRequest(name="山田 太郎", invoice_registration_number=None)
        updated = service.update_profile(dto)
        assert updated.invoice_registration_number is None
