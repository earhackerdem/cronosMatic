from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class ProductCategory:
    """Minimal category info embedded in a Product for response serialization."""

    id: int
    name: str
    slug: str


@dataclass
class Product:
    category_id: int
    name: str
    slug: str
    sku: str
    price: Decimal
    description: str | None = None
    stock_quantity: int = 0
    brand: str | None = None
    movement_type: str | None = None
    image_path: str | None = None
    is_active: bool = True
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Embedded category data — populated when eagerly loaded
    category: ProductCategory | None = None
