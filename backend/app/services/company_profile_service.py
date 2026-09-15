from datetime import datetime

from app.models.company_profile import CompanyProfile
from app.repositories.company_profile_repository import CompanyProfileRepository
from app.schemas.company_profile import CompanyProfileUpdateRequest


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class CompanyProfileService:
    def __init__(self, company_profile_repository: CompanyProfileRepository):
        self.company_profile_repository = company_profile_repository

    def get_profile(self) -> CompanyProfile:
        profile = self.company_profile_repository.get()
        if profile is None:
            profile = CompanyProfile(id=1, name="", updated_at=_now_iso())
        return profile

    def update_profile(self, dto: CompanyProfileUpdateRequest) -> CompanyProfile:
        profile = CompanyProfile(
            id=1,
            name=dto.name,
            business_name=dto.business_name,
            address=dto.address,
            contact_info=dto.contact_info,
            invoice_registration_number=dto.invoice_registration_number,
            updated_at=_now_iso(),
        )
        return self.company_profile_repository.upsert(profile)
