from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, computed_field

from app.domain.order.entity import OrderStatus, PaymentStatus


# ─── Request schemas ──────────────────────────────────────────────────────────


class GuestAddressInput(BaseModel):
    first_name: str
    last_name: str
    company: str | None = None
    address_line_1: str
    address_line_2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str
    phone: str | None = None


class CreateOrderRequest(BaseModel):
    shipping_address_id: int | None = None
    billing_address_id: int | None = None
    guest_email: str | None = None
    shipping_address: GuestAddressInput | None = None
    billing_address: GuestAddressInput | None = None
    payment_method: str
    shipping_method_name: str | None = None
    notes: str | None = None


# ─── Response schemas ─────────────────────────────────────────────────────────

_STATUS_LABELS: dict[str, str] = {
    "pending_payment": "Pending Payment",
    "processing": "Processing",
    "shipped": "Shipped",
    "delivered": "Delivered",
    "cancelled": "Cancelled",
}

_PAYMENT_LABELS: dict[str, str] = {
    "pending": "Pending",
    "paid": "Paid",
    "failed": "Failed",
    "refunded": "Refunded",
}


class OrderItemResponse(BaseModel):
    id: int
    product_id: int | None
    product_name: str
    quantity: int
    price_per_unit: Decimal
    total_price: Decimal

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: int
    order_number: str
    status: OrderStatus
    payment_status: PaymentStatus
    subtotal_amount: Decimal
    shipping_cost: Decimal
    total_amount: Decimal
    user_id: int | None = None
    guest_email: str | None = None
    shipping_address_id: int | None = None
    billing_address_id: int | None = None
    payment_gateway: str | None = None
    payment_id: str | None = None
    shipping_method_name: str | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    items: list[OrderItemResponse] = []

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def status_label(self) -> str:
        return _STATUS_LABELS.get(self.status.value, self.status.value)

    @computed_field
    @property
    def payment_status_label(self) -> str:
        return _PAYMENT_LABELS.get(self.payment_status.value, self.payment_status.value)

    @computed_field
    @property
    def email(self) -> str | None:
        return self.guest_email


class CreateOrderResponse(BaseModel):
    order: OrderResponse
    payment: dict


class OrderSummaryResponse(BaseModel):
    id: int
    order_number: str
    status: OrderStatus
    payment_status: PaymentStatus
    total_amount: Decimal
    created_at: datetime | None = None
    item_count: int = 0

    model_config = {"from_attributes": True}


class PaginatedOrdersResponse(BaseModel):
    items: list[OrderSummaryResponse]
    total: int
    page: int
    pages: int
    size: int
