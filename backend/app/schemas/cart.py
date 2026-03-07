from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.config import settings


class CartItemProductResponse(BaseModel):
    id: int
    name: str
    slug: str
    price: Decimal
    stock_quantity: int
    image_path: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def image_url(self) -> str | None:
        if self.image_path is None:
            return None
        if self.image_path.startswith("http"):
            return self.image_path
        base = settings.storage_base_url.rstrip("/")
        return f"{base}/{self.image_path}" if base else self.image_path


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    product: CartItemProductResponse
    quantity: int
    unit_price: Decimal
    total_price: Decimal

    model_config = ConfigDict(from_attributes=True)


class CartSummary(BaseModel):
    subtotal: Decimal
    total_items: int


class CartResponse(BaseModel):
    id: int
    user_id: int | None
    session_id: str | None
    total_items: int
    total_amount: Decimal
    items: list[CartItemResponse]
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summary(self) -> CartSummary:
        return CartSummary(
            subtotal=self.total_amount,
            total_items=self.total_items,
        )


class AddCartItemRequest(BaseModel):
    product_id: int
    quantity: int = Field(ge=1)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(ge=1)


class MergeCartRequest(BaseModel):
    session_id: str
