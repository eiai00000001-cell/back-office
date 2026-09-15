from datetime import datetime

from app.exceptions import NotFoundError
from app.models.client import Client
from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientCreateRequest, ClientUpdateRequest


class ClientNotFoundError(NotFoundError):
    pass


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ClientService:
    def __init__(self, client_repository: ClientRepository):
        self.client_repository = client_repository

    def create_client(self, dto: ClientCreateRequest) -> Client:
        now = _now_iso()
        client = Client(
            name=dto.name,
            postal_code=dto.postal_code,
            address=dto.address,
            contact_person=dto.contact_person,
            contact_info=dto.contact_info,
            created_at=now,
            updated_at=now,
        )
        return self.client_repository.create(client)

    def update_client(self, client_id: int, dto: ClientUpdateRequest) -> Client:
        client = self.client_repository.find_by_id(client_id)
        if client is None:
            raise ClientNotFoundError(f"client {client_id} not found")
        client.name = dto.name
        client.postal_code = dto.postal_code
        client.address = dto.address
        client.contact_person = dto.contact_person
        client.contact_info = dto.contact_info
        client.updated_at = _now_iso()
        return self.client_repository.update(client)

    def get_client(self, client_id: int) -> Client:
        client = self.client_repository.find_by_id(client_id)
        if client is None:
            raise ClientNotFoundError(f"client {client_id} not found")
        return client

    def list_clients(self) -> list[Client]:
        return self.client_repository.list_all()
