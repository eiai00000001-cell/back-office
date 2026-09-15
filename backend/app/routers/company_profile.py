from fastapi import APIRouter, Depends

from app.dependencies import get_company_profile_service
from app.schemas.company_profile import CompanyProfileResponse, CompanyProfileUpdateRequest
from app.services.company_profile_service import CompanyProfileService

router = APIRouter(prefix="/api/company-profile", tags=["company-profile"])


@router.get("", response_model=CompanyProfileResponse)
def get_company_profile(service: CompanyProfileService = Depends(get_company_profile_service)):
    return service.get_profile()


@router.put("", response_model=CompanyProfileResponse)
def update_company_profile(
    dto: CompanyProfileUpdateRequest, service: CompanyProfileService = Depends(get_company_profile_service)
):
    return service.update_profile(dto)
