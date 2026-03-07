from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.db.engine import get_db_session
from app.repositories.cart_repository import CartRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.cart import (
    AddCartItemRequest,
    CartResponse,
    MergeCartRequest,
    UpdateCartItemRequest,
)
from app.services.auth import AuthService, InvalidTokenError
from app.services.cart import (
    CartItemNotFoundError,
    CartOwnershipError,
    CartService,
    InsufficientStockError,
    ProductUnavailableError,
)
from app.repositories.user_repository import UserRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository


# ─── DI ──────────────────────────────────────────────────────────────────────


async def get_cart_service(
    session: AsyncSession = Depends(get_db_session),
) -> CartService:
    cart_repo = CartRepository(session)
    product_repo = ProductRepository(session)
    return CartService(cart_repo, product_repo)


async def get_cart_owner(
    authorization: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    session: AsyncSession = Depends(get_db_session),
) -> tuple[int | None, str | None]:
    """Resolve caller identity: (user_id, session_id).

    Raises 400 if neither credential is provided.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ")
        user_repo = UserRepository(session)
        rt_repo = RefreshTokenRepository(session)
        auth_service = AuthService(user_repo, rt_repo, settings)
        try:
            payload = auth_service.decode_access_token(token)
        except InvalidTokenError as exc:
            raise HTTPException(status_code=401, detail=str(exc))
        user_id = int(payload["sub"])
        return (user_id, None)

    if x_session_id:
        return (None, x_session_id)

    raise HTTPException(
        status_code=400,
        detail="Authorization header or X-Session-ID header is required.",
    )


# ─── Router ───────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartResponse)
async def get_cart(
    owner: Annotated[tuple[int | None, str | None], Depends(get_cart_owner)],
    service: Annotated[CartService, Depends(get_cart_service)],
):
    user_id, session_id = owner
    cart = await service.get_or_create_cart(user_id=user_id, session_id=session_id)
    return cart


@router.post("/items", response_model=CartResponse, status_code=201)
async def add_cart_item(
    body: AddCartItemRequest,
    owner: Annotated[tuple[int | None, str | None], Depends(get_cart_owner)],
    service: Annotated[CartService, Depends(get_cart_service)],
):
    user_id, session_id = owner
    cart = await service.get_or_create_cart(user_id=user_id, session_id=session_id)
    try:
        cart = await service.add_item(cart, body.product_id, body.quantity)
    except ProductUnavailableError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except InsufficientStockError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return cart


@router.put("/items/{cart_item_id}", response_model=CartResponse)
async def update_cart_item(
    cart_item_id: int,
    body: UpdateCartItemRequest,
    owner: Annotated[tuple[int | None, str | None], Depends(get_cart_owner)],
    service: Annotated[CartService, Depends(get_cart_service)],
):
    user_id, session_id = owner
    cart = await service.get_or_create_cart(user_id=user_id, session_id=session_id)
    try:
        cart = await service.update_item(cart, cart_item_id, body.quantity)
    except CartItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except CartOwnershipError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except InsufficientStockError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return cart


@router.delete("/items/{cart_item_id}", response_model=CartResponse, status_code=200)
async def remove_cart_item(
    cart_item_id: int,
    owner: Annotated[tuple[int | None, str | None], Depends(get_cart_owner)],
    service: Annotated[CartService, Depends(get_cart_service)],
):
    user_id, session_id = owner
    cart = await service.get_or_create_cart(user_id=user_id, session_id=session_id)
    try:
        cart = await service.remove_item(cart, cart_item_id)
    except CartItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except CartOwnershipError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return cart


@router.delete("", response_model=CartResponse, status_code=200)
async def clear_cart(
    owner: Annotated[tuple[int | None, str | None], Depends(get_cart_owner)],
    service: Annotated[CartService, Depends(get_cart_service)],
):
    user_id, session_id = owner
    cart = await service.get_or_create_cart(user_id=user_id, session_id=session_id)
    cart = await service.clear_cart(cart)
    return cart


@router.post("/merge", response_model=CartResponse)
async def merge_cart(
    body: MergeCartRequest,
    service: Annotated[CartService, Depends(get_cart_service)],
    current_user=Depends(get_current_user),
):
    user_cart = await service.get_or_create_cart(user_id=current_user.id)
    cart = await service.merge_guest_cart(user_cart, body.session_id)
    return cart
