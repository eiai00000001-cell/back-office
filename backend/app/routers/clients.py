from fastapi import APIRouter, Depends

from app.dependencies import get_client_service
from app.schemas.client import ClientCreateRequest, ClientResponse, ClientUpdateRequest
from app.services.client_service import ClientService
from app.schemas.common import EntityId

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("", response_model=list[ClientResponse])
def list_clients(service: ClientService = Depends(get_client_service)):
    return service.list_clients()


@router.post("", response_model=ClientResponse, status_code=201)
def create_client(dto: ClientCreateRequest, service: ClientService = Depends(get_client_service)):
    return service.create_client(dto)


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: EntityId, service: ClientService = Depends(get_client_service)):
    return service.get_client(client_id)


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: EntityId, dto: ClientUpdateRequest, service: ClientService = Depends(get_client_service)
):
    return service.update_client(client_id, dto)
