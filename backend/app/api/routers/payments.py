from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.config import settings
from app.db.engine import get_db_session
from app.domain.order.entity import PaymentStatus
from app.domain.user.entity import User
from app.repositories.address_repository import AddressRepository
from app.repositories.cart_repository import CartRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.payment import (
    CapturePayPalOrderRequest,
    CapturePayPalOrderResponse,
    CreatePayPalOrderRequest,
    CreatePayPalOrderResponse,
    SimulateFailureResponse,
    SimulatePaymentRequest,
    SimulateSuccessResponse,
    VerifyConfigResponse,
)
from app.services.auth import AuthService, InvalidTokenError
from app.services.cart import CartService
from app.services.order import OrderService
from app.services.paypal import PayPalAPIError, PayPalAuthError, PayPalPaymentService

router = APIRouter(prefix="/payments/paypal", tags=["payments"])


# ─── DI ──────────────────────────────────────────────────────────────────────


async def get_payment_owner(
    authorization: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
    session: AsyncSession = Depends(get_db_session),
) -> tuple[int | None, str | None]:
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
        status_code=401, detail="Authentication or X-Session-ID header is required."
    )


async def get_order_service(
    session: AsyncSession = Depends(get_db_session),
) -> OrderService:
    return OrderService(
        OrderRepository(session),
        CartRepository(session),
        AddressRepository(session),
        session,
    )


async def get_cart_service(
    session: AsyncSession = Depends(get_db_session),
) -> CartService:
    return CartService(CartRepository(session), ProductRepository(session))


# ─── Helpers ─────────────────────────────────────────────────────────────────


async def _get_order_for_payment(
    order_id: int, user_id: int | None, order_service: OrderService
):
    """Look up order by ID, validate ownership and payment status."""
    order = await order_service.order_repository.get_by_id(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    # Ownership check: authenticated user must match
    if user_id is not None and order.user_id != user_id:
        raise HTTPException(status_code=404, detail="Order not found.")
    if order.payment_status != PaymentStatus.pending:
        raise HTTPException(
            status_code=422, detail="Order payment_status must be 'pending'."
        )
    return order


async def _clear_cart_for_owner(
    user_id: int | None,
    session_id: str | None,
    cart_service: CartService,
) -> None:
    """Clear the cart for the given owner, if it exists."""
    if user_id is not None:
        cart = await cart_service.cart_repository.get_by_user_id(user_id)
    elif session_id is not None:
        cart = await cart_service.cart_repository.get_by_session_id(session_id)
    else:
        cart = None
    if cart is not None:
        await cart_service.clear_cart(cart)


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/create-order", response_model=CreatePayPalOrderResponse)
async def create_paypal_order(
    body: CreatePayPalOrderRequest,
    owner: Annotated[tuple[int | None, str | None], Depends(get_payment_owner)],
    order_service: Annotated[OrderService, Depends(get_order_service)],
) -> CreatePayPalOrderResponse:
    user_id, _session_id = owner
    order = await _get_order_for_payment(body.order_id, user_id, order_service)

    # Resolve shipping address
    shipping_address = None
    if order.shipping_address_id:
        addr = await order_service.address_repository.get_by_id(
            order.shipping_address_id
        )
        if addr:
            shipping_address = {
                "first_name": addr.first_name,
                "last_name": addr.last_name,
                "address_line_1": addr.address_line_1,
                "address_line_2": addr.address_line_2 or "",
                "city": addr.city,
                "state": addr.state,
                "postal_code": addr.postal_code,
                "country": addr.country,
            }

    if shipping_address is None:
        shipping_address = {
            "first_name": "Customer",
            "last_name": "",
            "address_line_1": "",
            "city": "",
            "state": "",
            "postal_code": "",
            "country": settings.payment_country_code,
        }

    paypal_service = PayPalPaymentService()
    try:
        result = await paypal_service.create_order(order, shipping_address)
    except (PayPalAuthError, PayPalAPIError) as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return CreatePayPalOrderResponse(
        paypal_order_id=result["paypal_order_id"],
        approval_url=result["approval_url"],
        order_number=order.order_number,
    )


@router.post("/capture-order", response_model=CapturePayPalOrderResponse)
async def capture_paypal_order(
    body: CapturePayPalOrderRequest,
    owner: Annotated[tuple[int | None, str | None], Depends(get_payment_owner)],
    order_service: Annotated[OrderService, Depends(get_order_service)],
    cart_service: Annotated[CartService, Depends(get_cart_service)],
) -> CapturePayPalOrderResponse:
    user_id, session_id = owner
    order = await _get_order_for_payment(body.order_id, user_id, order_service)

    paypal_service = PayPalPaymentService()
    try:
        result = await paypal_service.capture_order(body.paypal_order_id)
    except (PayPalAuthError, PayPalAPIError) as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    updated_order = await order_service.update_payment_status(
        order, PaymentStatus.paid, result["capture_id"], "paypal"
    )
    await _clear_cart_for_owner(user_id, session_id, cart_service)

    return CapturePayPalOrderResponse(
        order_number=updated_order.order_number,
        payment_status=updated_order.payment_status.value,
        capture_id=result["capture_id"],
    )


@router.post("/simulate-success", response_model=SimulateSuccessResponse)
async def simulate_payment_success(
    body: SimulatePaymentRequest,
    owner: Annotated[tuple[int | None, str | None], Depends(get_payment_owner)],
    order_service: Annotated[OrderService, Depends(get_order_service)],
    cart_service: Annotated[CartService, Depends(get_cart_service)],
) -> SimulateSuccessResponse:
    if not settings.paypal_simulate_payments:
        raise HTTPException(status_code=403, detail="Payment simulation is disabled.")

    user_id, session_id = owner
    order = await _get_order_for_payment(body.order_id, user_id, order_service)

    paypal_service = PayPalPaymentService()
    result = paypal_service.simulate_success(order)

    await order_service.update_payment_status(
        order, PaymentStatus.paid, result["capture_id"], "paypal"
    )
    await _clear_cart_for_owner(user_id, session_id, cart_service)

    return SimulateSuccessResponse(
        order_number=order.order_number,
        payment_status="paid",
        simulated=True,
        paypal_order_id=result["paypal_order_id"],
        capture_id=result["capture_id"],
    )


@router.post("/simulate-failure", response_model=SimulateFailureResponse)
async def simulate_payment_failure(
    body: SimulatePaymentRequest,
    owner: Annotated[tuple[int | None, str | None], Depends(get_payment_owner)],
    order_service: Annotated[OrderService, Depends(get_order_service)],
) -> SimulateFailureResponse:
    if not settings.paypal_simulate_payments:
        raise HTTPException(status_code=403, detail="Payment simulation is disabled.")

    user_id, _session_id = owner
    order = await _get_order_for_payment(body.order_id, user_id, order_service)

    paypal_service = PayPalPaymentService()
    result = paypal_service.simulate_failure(order)

    await order_service.update_payment_status(
        order, PaymentStatus.failed, result["paypal_order_id"], "paypal"
    )

    return SimulateFailureResponse(
        order_number=order.order_number,
        payment_status="failed",
        simulated=True,
        paypal_order_id=result["paypal_order_id"],
        error=result["error"],
    )


@router.get("/verify-config", response_model=VerifyConfigResponse)
async def verify_paypal_config(
    _admin: Annotated[User, Depends(require_admin)],
) -> VerifyConfigResponse:
    paypal_service = PayPalPaymentService()
    try:
        await paypal_service.get_access_token()
        auth_test = "success"
    except PayPalAuthError as exc:
        auth_test = str(exc)

    return VerifyConfigResponse(
        mode=settings.paypal_mode,
        client_id_configured=bool(settings.paypal_client_id),
        client_secret_configured=bool(settings.paypal_client_secret),
        simulate_payments=settings.paypal_simulate_payments,
        base_url=paypal_service._base_url,
        auth_test=auth_test,
    )
