from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.domain.cart.entity import Cart
from app.domain.cart.repository import CartRepositoryInterface
from app.domain.product.repository import ProductRepositoryInterface


# ─── Exceptions ──────────────────────────────────────────────────────────────


class CartItemNotFoundError(ValueError):
    """Raised when the cart item does not exist."""


class CartOwnershipError(PermissionError):
    """Raised when a cart item does not belong to the caller's cart."""


class ProductUnavailableError(ValueError):
    """Raised when the product is not found or is inactive."""


class InsufficientStockError(ValueError):
    """Raised when the requested quantity exceeds available stock."""


# ─── Service ─────────────────────────────────────────────────────────────────


class CartService:
    def __init__(
        self,
        cart_repository: CartRepositoryInterface,
        product_repository: ProductRepositoryInterface,
    ):
        self.cart_repository = cart_repository
        self.product_repository = product_repository

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _recalculate_totals(self, cart: Cart) -> None:
        """Recalculate total_items and total_amount from cart.items in-place."""
        cart.total_items = sum(item.quantity for item in cart.items)
        cart.total_amount = sum(
            (item.total_price for item in cart.items), Decimal("0.00")
        )

    async def _reload_cart(self, cart: Cart) -> Cart:
        """Reload the cart from the repository to get fresh item data."""
        if cart.user_id is not None:
            reloaded = await self.cart_repository.get_by_user_id(cart.user_id)
        else:
            reloaded = await self.cart_repository.get_by_session_id(cart.session_id)
        return reloaded or cart

    # ─── Public methods ───────────────────────────────────────────────────────

    async def get_or_create_cart(
        self,
        user_id: int | None = None,
        session_id: str | None = None,
    ) -> Cart:
        if user_id is not None:
            cart = await self.cart_repository.get_by_user_id(user_id)
            if cart is None:
                cart = await self.cart_repository.create(
                    Cart(user_id=user_id, expires_at=None)
                )
            return cart

        if session_id is not None:
            cart = await self.cart_repository.get_by_session_id(session_id)
            if cart is None:
                expires_at = datetime.now(timezone.utc) + timedelta(days=7)
                cart = await self.cart_repository.create(
                    Cart(session_id=session_id, expires_at=expires_at)
                )
            return cart

        raise ValueError("Either user_id or session_id must be provided.")

    async def add_item(self, cart: Cart, product_id: int, quantity: int) -> Cart:
        # Fetch and validate product
        product = await self.product_repository.get_by_id(product_id)
        if product is None:
            raise ProductUnavailableError("Product not found")
        if not product.is_active:
            raise ProductUnavailableError("Product is not available")

        # Check if product already in cart
        existing_item = next(
            (item for item in cart.items if item.product_id == product_id), None
        )

        if existing_item is not None:
            new_qty = existing_item.quantity + quantity
            if new_qty > product.stock_quantity:
                raise InsufficientStockError("Insufficient stock")
            await self.cart_repository.update_item(
                existing_item.id, new_qty, product.price
            )
        else:
            if quantity > product.stock_quantity:
                raise InsufficientStockError("Insufficient stock")
            await self.cart_repository.add_item(
                cart.id, product_id, quantity, product.price
            )

        # Reload cart, recalculate totals, persist
        reloaded = await self._reload_cart(cart)
        self._recalculate_totals(reloaded)
        return await self.cart_repository.save(reloaded)

    async def update_item(self, cart: Cart, cart_item_id: int, quantity: int) -> Cart:
        item = await self.cart_repository.get_item_by_id(cart_item_id)
        if item is None:
            raise CartItemNotFoundError(f"Cart item with id {cart_item_id} not found.")
        if item.cart_id != cart.id:
            raise CartOwnershipError("Permission denied")

        product = await self.product_repository.get_by_id(item.product_id)
        if product is None:
            raise ProductUnavailableError("Product not found")
        if quantity > product.stock_quantity:
            raise InsufficientStockError("Insufficient stock")

        await self.cart_repository.update_item(cart_item_id, quantity, product.price)

        reloaded = await self._reload_cart(cart)
        self._recalculate_totals(reloaded)
        return await self.cart_repository.save(reloaded)

    async def remove_item(self, cart: Cart, cart_item_id: int) -> Cart:
        item = await self.cart_repository.get_item_by_id(cart_item_id)
        if item is None:
            raise CartItemNotFoundError(f"Cart item with id {cart_item_id} not found.")
        if item.cart_id != cart.id:
            raise CartOwnershipError("Permission denied")

        await self.cart_repository.delete_item(cart_item_id)

        reloaded = await self._reload_cart(cart)
        self._recalculate_totals(reloaded)
        return await self.cart_repository.save(reloaded)

    async def clear_cart(self, cart: Cart) -> Cart:
        await self.cart_repository.clear_items(cart.id)
        cart.total_items = 0
        cart.total_amount = Decimal("0.00")
        cart.items = []
        return await self.cart_repository.save(cart)

    async def merge_guest_cart(self, user_cart: Cart, session_id: str) -> Cart:
        guest_cart = await self.cart_repository.get_by_session_id(session_id)
        if guest_cart is None:
            return user_cart

        for guest_item in guest_cart.items:
            product = await self.product_repository.get_by_id(guest_item.product_id)
            if product is None or not product.is_active:
                continue  # skip silently

            existing = next(
                (i for i in user_cart.items if i.product_id == guest_item.product_id),
                None,
            )

            if existing is not None:
                new_qty = existing.quantity + guest_item.quantity
                if new_qty > product.stock_quantity:
                    continue  # silently discard
                await self.cart_repository.update_item(
                    existing.id, new_qty, product.price
                )
            else:
                if guest_item.quantity > product.stock_quantity:
                    continue  # silently discard
                await self.cart_repository.add_item(
                    user_cart.id,
                    guest_item.product_id,
                    guest_item.quantity,
                    product.price,
                )

        # Delete guest cart
        await self.cart_repository.delete_cart(guest_cart.id)

        # Reload user cart, recalculate totals, persist
        reloaded = await self._reload_cart(user_cart)
        self._recalculate_totals(reloaded)
        return await self.cart_repository.save(reloaded)
