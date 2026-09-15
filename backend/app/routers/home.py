from fastapi import APIRouter, Depends

from app.dependencies import get_home_summary_service
from app.schemas.home import HomeSummaryResponse
from app.services.home_summary_service import HomeSummaryService

router = APIRouter(prefix="/api/home", tags=["home"])


@router.get("/summary", response_model=HomeSummaryResponse)
def get_home_summary(service: HomeSummaryService = Depends(get_home_summary_service)):
    return service.get_summary()
