from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.expense import Expense
from app.models.invoice import Invoice
from app.models.project import Project
from app.models.quote import Quote


class ProjectRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_id(self, project_id: int) -> Project | None:
        return self.session.get(Project, project_id)

    def list_all(
        self, status: str | None = None, client_id: int | None = None
    ) -> list[tuple[Project, str | None, int, int]]:
        """案件を取引先名・見積件数・請求件数付きで取得する(詳細設計書4.9.3)。"""
        quote_count = (
            select(func.count(Quote.id)).where(Quote.project_id == Project.id).correlate(Project).scalar_subquery()
        )
        invoice_count = (
            select(func.count(Invoice.id)).where(Invoice.project_id == Project.id).correlate(Project).scalar_subquery()
        )
        stmt = (
            select(Project, Client.name, quote_count, invoice_count)
            .outerjoin(Client, Client.id == Project.client_id)
            .order_by(Project.due_date.is_(None), Project.due_date.asc(), Project.id.asc())
        )
        if status is not None:
            stmt = stmt.where(Project.status == status)
        if client_id is not None:
            stmt = stmt.where(Project.client_id == client_id)
        return [(p, cname, qc, ic) for p, cname, qc, ic in self.session.execute(stmt).all()]

    def create(self, project: Project) -> Project:
        self.session.add(project)
        self.session.flush()
        return project

    def update(self, project: Project) -> Project:
        self.session.flush()
        return project

    def update_status(self, project: Project, status: str, updated_at: str) -> Project:
        project.status = status
        project.updated_at = updated_at
        self.session.flush()
        return project

    def delete(self, project: Project) -> None:
        """書類の紐付けを解除してから案件を削除する(詳細設計書4.9.6)。updated_atは更新しない。"""
        for model in (Invoice, Quote, Expense):
            self.session.execute(update(model).where(model.project_id == project.id).values(project_id=None))
        self.session.expire_all()
        self.session.delete(project)
        self.session.flush()

    # 段階2(F-10 通知)で使用予定。段階1では未使用。
    def list_due_before(self, before: str) -> list[Project]:
        stmt = (
            select(Project)
            .where(Project.due_date.is_not(None), Project.due_date <= before, Project.status != "DONE")
            .order_by(Project.due_date, Project.id)
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_quotes(self, project_id: int) -> list[Quote]:
        stmt = select(Quote).where(Quote.project_id == project_id).order_by(Quote.id.desc())
        return list(self.session.execute(stmt).scalars().all())

    def list_invoices(self, project_id: int) -> list[Invoice]:
        stmt = select(Invoice).where(Invoice.project_id == project_id).order_by(Invoice.id.desc())
        return list(self.session.execute(stmt).scalars().all())
