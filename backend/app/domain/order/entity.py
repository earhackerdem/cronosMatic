from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


class OrderStatus(str, Enum):
    pending_payment = "pending_payment"
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


class PaymentStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


@dataclass
class OrderItem:
    order_id: int
    product_id: int | None
    product_name: str
    quantity: int
    price_per_unit: Decimal
    total_price: Decimal
    id: int | None = None


@dataclass
class Order:
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
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    items: list[OrderItem] = field(default_factory=list)
