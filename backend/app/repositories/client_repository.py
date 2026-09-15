from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.client import Client


class ClientRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_id(self, client_id: int) -> Client | None:
        return self.session.get(Client, client_id)

    def list_all(self) -> list[Client]:
        stmt = select(Client).order_by(Client.id)
        return list(self.session.execute(stmt).scalars().all())

    def create(self, client: Client) -> Client:
        self.session.add(client)
        self.session.flush()
        return client

    def update(self, client: Client) -> Client:
        self.session.flush()
        return client
