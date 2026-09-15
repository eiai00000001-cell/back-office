from pydantic import BaseModel


class HomeSummaryResponse(BaseModel):
    unpaid_count: int
    overdue_count: int
