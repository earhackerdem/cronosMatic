from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.engine import get_db_session
from app.domain.address.exceptions import AddressNotFoundError
from app.domain.user.entity import User
from app.repositories.address_repository import AddressRepository
from app.schemas.address import AddressCreate, AddressResponse, AddressUpdate
from app.services.address import AddressService


# ─── DI ──────────────────────────────────────────────────────────────────────


async def get_address_service(
    session: AsyncSession = Depends(get_db_session),
) -> AddressService:
    repository = AddressRepository(session)
    return AddressService(repository)


# ─── Router ───────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/user/addresses", tags=["addresses"])


@router.get("", response_model=list[AddressResponse])
async def list_addresses(
    type: str | None = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    service: Annotated[AddressService, Depends(get_address_service)] = None,
):
    addresses = await service.list_addresses(current_user.id, type=type)
    return [AddressResponse.model_validate(a.__dict__) for a in addresses]


@router.post("", response_model=AddressResponse, status_code=201)
async def create_address(
    body: AddressCreate,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    service: Annotated[AddressService, Depends(get_address_service)] = None,
):
    address = await service.create_address(current_user.id, body.model_dump())
    return AddressResponse.model_validate(address.__dict__)


@router.get("/{address_id}", response_model=AddressResponse)
async def get_address(
    address_id: int,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    service: Annotated[AddressService, Depends(get_address_service)] = None,
):
    try:
        address = await service.get_address(current_user.id, address_id)
    except AddressNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return AddressResponse.model_validate(address.__dict__)


@router.put("/{address_id}", response_model=AddressResponse)
async def update_address(
    address_id: int,
    body: AddressUpdate,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    service: Annotated[AddressService, Depends(get_address_service)] = None,
):
    try:
        address = await service.update_address(
            current_user.id,
            address_id,
            body.model_dump(exclude_unset=True),
        )
    except AddressNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return AddressResponse.model_validate(address.__dict__)


@router.delete("/{address_id}", status_code=204)
async def delete_address(
    address_id: int,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    service: Annotated[AddressService, Depends(get_address_service)] = None,
):
    try:
        await service.delete_address(current_user.id, address_id)
    except AddressNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(status_code=204)


@router.patch("/{address_id}/set-default", response_model=AddressResponse)
async def set_default(
    address_id: int,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    service: Annotated[AddressService, Depends(get_address_service)] = None,
):
    try:
        address = await service.set_default(current_user.id, address_id)
    except AddressNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return AddressResponse.model_validate(address.__dict__)
