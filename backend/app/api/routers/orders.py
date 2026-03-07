import math
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.db.engine import get_db_session
from app.domain.order.exceptions import OrderNotFoundError
from app.domain.user.entity import User
from app.repositories.address_repository import AddressRepository
from app.repositories.cart_repository import CartRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.user_repository import UserRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.schemas.order import (
    CreateOrderRequest,
    CreateOrderResponse,
    OrderResponse,
    OrderSummaryResponse,
    PaginatedOrdersResponse,
)
from app.services.auth import AuthService, InvalidTokenError
from app.services.cart import InsufficientStockError
from app.services.order import OrderService


# ─── DI ──────────────────────────────────────────────────────────────────────


async def get_order_service(
    session: AsyncSession = Depends(get_db_session),
) -> OrderService:
    order_repo = OrderRepository(session)
    cart_repo = CartRepository(session)
    address_repo = AddressRepository(session)
    return OrderService(order_repo, cart_repo, address_repo, session)


async def get_order_owner(
    authorization: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    session: AsyncSession = Depends(get_db_session),
) -> tuple[int | None, str | None]:
    """Resolve caller identity: (user_id, session_id) for order creation.

    Raises 401 if neither credential is provided.
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
        status_code=401,
        detail="Authentication or X-Session-ID header is required.",
    )


# ─── Router ───────────────────────────────────────────────────────────────────

router = APIRouter(tags=["orders"])


@router.post("/orders", response_model=CreateOrderResponse, status_code=201)
async def create_order(
    body: CreateOrderRequest,
    owner: Annotated[tuple[int | None, str | None], Depends(get_order_owner)],
    service: Annotated[OrderService, Depends(get_order_service)],
):
    user_id, session_id = owner
    try:
        order = await service.create_order_from_cart(
            user_id=user_id,
            session_id=session_id,
            guest_email=body.guest_email,
            shipping_address_id=body.shipping_address_id,
            billing_address_id=body.billing_address_id,
            guest_shipping_address=body.shipping_address.model_dump()
            if body.shipping_address
            else None,
            guest_billing_address=body.billing_address.model_dump()
            if body.billing_address
            else None,
            payment_method=body.payment_method,
            shipping_method_name=body.shipping_method_name,
            notes=body.notes,
        )
    except InsufficientStockError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    order_response = OrderResponse.model_validate(
        order.__dict__ | {"items": [i.__dict__ for i in order.items]}
    )
    payment = {
        "method": body.payment_method,
        "status": order.payment_status.value,
        "redirect_url": None,
    }
    return CreateOrderResponse(order=order_response, payment=payment)


@router.get("/user/orders", response_model=PaginatedOrdersResponse)
async def list_orders(
    page: int = 1,
    size: int = 10,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    service: Annotated[OrderService, Depends(get_order_service)] = None,
):
    if page < 1:
        raise HTTPException(status_code=422, detail="page must be >= 1")
    if size < 1 or size > 100:
        raise HTTPException(status_code=422, detail="size must be between 1 and 100")

    orders, total = await service.get_user_orders(current_user.id, page, size)
    pages = math.ceil(total / size) if size > 0 else 0

    items = [
        OrderSummaryResponse(
            id=o.id,
            order_number=o.order_number,
            status=o.status,
            payment_status=o.payment_status,
            total_amount=o.total_amount,
            created_at=o.created_at,
            item_count=sum(i.quantity for i in o.items),
        )
        for o in orders
    ]
    return PaginatedOrdersResponse(
        items=items, total=total, page=page, pages=pages, size=size
    )


@router.get("/user/orders/{order_number}", response_model=OrderResponse)
async def get_order(
    order_number: str,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    service: Annotated[OrderService, Depends(get_order_service)] = None,
):
    try:
        order = await service.get_order_by_number(order_number, current_user.id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return OrderResponse.model_validate(
        order.__dict__ | {"items": [i.__dict__ for i in order.items]}
    )
