from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.address import AddressModel
    from app.models.product import ProductModel


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_unit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relationships
    product: Mapped[ProductModel | None] = relationship("ProductModel")


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_number: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    guest_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending_payment"
    )
    payment_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending"
    )
    shipping_address_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("addresses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    billing_address_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("addresses.id", ondelete="SET NULL"),
        nullable=True,
    )
    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_gateway: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shipping_method_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    items: Mapped[list[OrderItemModel]] = relationship(
        "OrderItemModel",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="OrderItemModel.order_id",
    )
    shipping_address: Mapped[AddressModel] = relationship(
        "AddressModel",
        foreign_keys=[shipping_address_id],
        lazy="selectin",
    )
    billing_address: Mapped[AddressModel | None] = relationship(
        "AddressModel",
        foreign_keys=[billing_address_id],
        lazy="selectin",
    )
