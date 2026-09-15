from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientCreateRequest, ClientUpdateRequest
from app.services.client_service import ClientNotFoundError, ClientService


class TestClientService:
    def test_create_client_persists_and_returns_client(self, db_session):
        service = ClientService(ClientRepository(db_session))
        dto = ClientCreateRequest(name="株式会社サンプル商事", postal_code="100-0001")
        client = service.create_client(dto)
        assert client.id is not None
        assert client.name == "株式会社サンプル商事"

    def test_list_clients_returns_created_clients(self, db_session):
        service = ClientService(ClientRepository(db_session))
        service.create_client(ClientCreateRequest(name="取引先A"))
        service.create_client(ClientCreateRequest(name="取引先B"))
        clients = service.list_clients()
        assert [c.name for c in clients] == ["取引先A", "取引先B"]

    def test_update_client_changes_fields(self, db_session):
        service = ClientService(ClientRepository(db_session))
        client = service.create_client(ClientCreateRequest(name="旧名称"))
        updated = service.update_client(client.id, ClientUpdateRequest(name="新名称"))
        assert updated.name == "新名称"

    def test_update_client_raises_not_found_for_unknown_id(self, db_session):
        service = ClientService(ClientRepository(db_session))
        try:
            service.update_client(999, ClientUpdateRequest(name="X"))
            assert False, "expected ClientNotFoundError"
        except ClientNotFoundError:
            pass
