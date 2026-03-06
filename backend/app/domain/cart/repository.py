from decimal import Decimal
from typing import Protocol

from app.domain.cart.entity import Cart, CartItem


class CartRepositoryInterface(Protocol):
    async def get_by_user_id(self, user_id: int) -> Cart | None:
        """Retrieve active cart by user_id (expires_at IS NULL OR expires_at > now())."""
        ...

    async def get_by_session_id(self, session_id: str) -> Cart | None:
        """Retrieve active non-expired cart by session_id."""
        ...

    async def create(self, cart: Cart) -> Cart:
        """Persist a new cart."""
        ...

    async def save(self, cart: Cart) -> Cart:
        """Persist an updated cart (totals, etc.)."""
        ...

    async def get_item_by_id(self, cart_item_id: int) -> CartItem | None:
        """Retrieve a cart item by its ID."""
        ...

    async def add_item(
        self,
        cart_id: int,
        product_id: int,
        quantity: int,
        unit_price: Decimal,
    ) -> CartItem:
        """Insert a new CartItem into the cart."""
        ...

    async def update_item(
        self,
        cart_item_id: int,
        quantity: int,
        unit_price: Decimal,
    ) -> CartItem:
        """Update quantity and recalculate total_price for an existing CartItem."""
        ...

    async def delete_item(self, cart_item_id: int) -> None:
        """Hard-delete a single CartItem."""
        ...

    async def clear_items(self, cart_id: int) -> None:
        """Hard-delete all CartItems belonging to cart_id."""
        ...

    async def delete_cart(self, cart_id: int) -> None:
        """Hard-delete the cart (cascade deletes items)."""
        ...
