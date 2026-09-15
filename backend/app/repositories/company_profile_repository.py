from sqlalchemy.orm import Session

from app.models.company_profile import CompanyProfile


class CompanyProfileRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self) -> CompanyProfile | None:
        return self.session.get(CompanyProfile, 1)

    def upsert(self, profile: CompanyProfile) -> CompanyProfile:
        self.session.merge(profile)
        self.session.flush()
        return self.get()
