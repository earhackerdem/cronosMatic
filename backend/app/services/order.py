import secrets
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.address.repository import AddressRepositoryProtocol
from app.domain.cart.repository import CartRepositoryInterface
from app.domain.order.entity import Order, OrderItem, OrderStatus, PaymentStatus
from app.domain.order.exceptions import OrderCancellationError, OrderNotFoundError
from app.domain.order.repository import OrderRepositoryProtocol
from app.models.address import AddressModel
from app.services.cart import InsufficientStockError


# ─── Cancellable statuses ─────────────────────────────────────────────────────

_CANCELLABLE_STATUSES = {OrderStatus.pending_payment, OrderStatus.processing}


class OrderService:
    def __init__(
        self,
        order_repository: OrderRepositoryProtocol,
        cart_repository: CartRepositoryInterface,
        address_repository: AddressRepositoryProtocol,
        session: AsyncSession,
    ) -> None:
        self.order_repository = order_repository
        self.cart_repository = cart_repository
        self.address_repository = address_repository
        self.session = session

    # ─── Helpers ─────────────────────────────────────────────────────────────

    async def _generate_order_number(self) -> str:
        year = datetime.now(timezone.utc).year
        for _ in range(10):
            candidate = f"CM-{year}-{secrets.token_hex(4).upper()}"
            if not await self.order_repository.order_number_exists(candidate):
                return candidate
        raise RuntimeError(
            "Failed to generate a unique order number after 10 attempts."
        )

    # ─── Public methods ───────────────────────────────────────────────────────

    async def create_order_from_cart(
        self,
        user_id: int | None,
        session_id: str | None,
        guest_email: str | None,
        shipping_address_id: int | None,
        billing_address_id: int | None,
        guest_shipping_address: dict | None,
        guest_billing_address: dict | None,
        payment_method: str,
        shipping_method_name: str | None = None,
        notes: str | None = None,
    ) -> Order:
        # Validate payment method
        if payment_method != "paypal":
            raise ValueError(
                f"Unsupported payment method: {payment_method}. Only 'paypal' is supported."
            )

        # Get cart
        if user_id is not None:
            cart = await self.cart_repository.get_by_user_id(user_id)
        elif session_id is not None:
            cart = await self.cart_repository.get_by_session_id(session_id)
        else:
            cart = None

        if cart is None or cart.total_items == 0:
            raise ValueError("Cart is empty")

        # Guest must provide email
        if user_id is None and not guest_email:
            raise ValueError("Guest email is required for guest checkout.")

        try:
            # Lock products for update
            product_ids = [item.product_id for item in cart.items]
            locked_products = await self.order_repository.lock_and_get_products(
                product_ids
            )
            product_map = {p.id: p for p in locked_products}

            # Check stock for each cart item
            for cart_item in cart.items:
                product = product_map.get(cart_item.product_id)
                if product is None or not product.is_active:
                    raise ValueError(
                        f"Product {cart_item.product_id} is no longer available."
                    )
                if product.stock_quantity < cart_item.quantity:
                    raise InsufficientStockError(
                        f"Insufficient stock for '{product.name}'. "
                        f"Requested {cart_item.quantity}, available {product.stock_quantity}."
                    )

            # Resolve shipping address
            if user_id is not None:
                # Authenticated: verify shipping address belongs to user
                if shipping_address_id is None:
                    raise ValueError(
                        "shipping_address_id is required for authenticated users."
                    )
                shipping_addr = await self.address_repository.get_by_id(
                    shipping_address_id
                )
                if shipping_addr is None or shipping_addr.user_id != user_id:
                    raise OrderNotFoundError(
                        f"Address {shipping_address_id} not found."
                    )
                resolved_shipping_id = shipping_address_id

                # Billing address (optional for auth users; defaults to None)
                if billing_address_id is not None:
                    billing_addr = await self.address_repository.get_by_id(
                        billing_address_id
                    )
                    if billing_addr is None or billing_addr.user_id != user_id:
                        raise OrderNotFoundError(
                            f"Address {billing_address_id} not found."
                        )
                    resolved_billing_id = billing_address_id
                else:
                    resolved_billing_id = None
            else:
                # Guest: create address models directly (bypass repo to stay in same transaction)
                if guest_shipping_address is None:
                    raise ValueError("Guest checkout requires a shipping address.")

                shipping_model = AddressModel(
                    user_id=None,
                    type="shipping",
                    first_name=guest_shipping_address["first_name"],
                    last_name=guest_shipping_address["last_name"],
                    company=guest_shipping_address.get("company"),
                    address_line_1=guest_shipping_address["address_line_1"],
                    address_line_2=guest_shipping_address.get("address_line_2"),
                    city=guest_shipping_address["city"],
                    state=guest_shipping_address["state"],
                    postal_code=guest_shipping_address["postal_code"],
                    country=guest_shipping_address["country"],
                    phone=guest_shipping_address.get("phone"),
                    is_default=False,
                )
                self.session.add(shipping_model)
                await self.session.flush()
                resolved_shipping_id = shipping_model.id

                if guest_billing_address is not None:
                    billing_model = AddressModel(
                        user_id=None,
                        type="billing",
                        first_name=guest_billing_address["first_name"],
                        last_name=guest_billing_address["last_name"],
                        company=guest_billing_address.get("company"),
                        address_line_1=guest_billing_address["address_line_1"],
                        address_line_2=guest_billing_address.get("address_line_2"),
                        city=guest_billing_address["city"],
                        state=guest_billing_address["state"],
                        postal_code=guest_billing_address["postal_code"],
                        country=guest_billing_address["country"],
                        phone=guest_billing_address.get("phone"),
                        is_default=False,
                    )
                    self.session.add(billing_model)
                    await self.session.flush()
                    resolved_billing_id = billing_model.id
                else:
                    resolved_billing_id = None

            # Calculate amounts
            subtotal = sum((item.total_price for item in cart.items), Decimal("0.00"))
            shipping_cost = settings.default_shipping_cost
            total = subtotal + shipping_cost

            # Generate unique order number
            order_number = await self._generate_order_number()

            # Build order items
            order_items = [
                OrderItem(
                    order_id=0,  # will be set after flush
                    product_id=cart_item.product_id,
                    product_name=product_map[cart_item.product_id].name,
                    quantity=cart_item.quantity,
                    price_per_unit=cart_item.unit_price,
                    total_price=cart_item.total_price,
                )
                for cart_item in cart.items
            ]

            # Decrement stock
            for cart_item in cart.items:
                product_map[cart_item.product_id].stock_quantity -= cart_item.quantity

            # Create order
            order = Order(
                order_number=order_number,
                user_id=user_id,
                guest_email=guest_email,
                status=OrderStatus.pending_payment,
                payment_status=PaymentStatus.pending,
                shipping_address_id=resolved_shipping_id,
                billing_address_id=resolved_billing_id,
                subtotal_amount=subtotal,
                shipping_cost=shipping_cost,
                total_amount=total,
                shipping_method_name=shipping_method_name,
                notes=notes,
                items=order_items,
            )
            await self.order_repository.create(order)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        # After transaction commits, fetch full order with all relations
        full_order = await self.order_repository.get_by_order_number(order_number)
        return full_order

    async def get_user_orders(
        self, user_id: int, page: int, size: int
    ) -> tuple[list[Order], int]:
        offset = (page - 1) * size
        return await self.order_repository.get_by_user_id(user_id, offset, size)

    async def get_order_by_number(self, order_number: str, user_id: int) -> Order:
        order = await self.order_repository.get_by_order_number(order_number)
        if order is None or order.user_id != user_id:
            raise OrderNotFoundError(f"Order {order_number} not found.")
        return order

    async def cancel_order(self, order_id: int, user_id: int) -> Order:
        order = await self.order_repository.get_by_id(order_id)
        if order is None or order.user_id != user_id:
            raise OrderNotFoundError(f"Order {order_id} not found.")
        if order.status not in _CANCELLABLE_STATUSES:
            raise OrderCancellationError(
                f"Order cannot be cancelled in status '{order.status.value}'."
            )

        # Restore stock
        product_ids = [item.product_id for item in order.items if item.product_id]
        locked_products = await self.order_repository.lock_and_get_products(product_ids)
        product_map = {p.id: p for p in locked_products}
        for item in order.items:
            if item.product_id and item.product_id in product_map:
                product_map[item.product_id].stock_quantity += item.quantity
        await self.session.flush()

        return await self.order_repository.update_status(
            order_id, OrderStatus.cancelled
        )

    async def update_payment_status(
        self,
        order: Order,
        payment_status: PaymentStatus,
        payment_id: str | None = None,
        payment_gateway: str | None = None,
    ) -> Order:
        updated = await self.order_repository.update_payment_status(
            order.id, payment_status, payment_id, payment_gateway
        )
        # Auto-transition to processing if paid
        if (
            payment_status == PaymentStatus.paid
            and updated.status == OrderStatus.pending_payment
        ):
            updated = await self.order_repository.update_status(
                order.id, OrderStatus.processing
            )
        return updated
