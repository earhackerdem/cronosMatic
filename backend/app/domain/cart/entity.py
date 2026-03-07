from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class CartItemProduct:
    """Minimal product info embedded in a CartItem for response serialization."""

    id: int
    name: str
    slug: str
    price: Decimal
    stock_quantity: int
    image_path: str | None = None


@dataclass
class CartItem:
    cart_id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    id: int | None = None
    product: CartItemProduct | None = None


@dataclass
class Cart:
    total_items: int = 0
    total_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    user_id: int | None = None
    session_id: str | None = None
    expires_at: datetime | None = None
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    items: list[CartItem] = field(default_factory=list)
