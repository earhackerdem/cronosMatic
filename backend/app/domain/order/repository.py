from typing import Protocol

from app.domain.order.entity import Order, OrderStatus, PaymentStatus


class OrderRepositoryProtocol(Protocol):
    async def create(self, order: Order) -> Order:
        """Persist a new order (flush only, service manages transaction)."""
        ...

    async def get_by_id(self, order_id: int) -> Order | None:
        """Retrieve an order by its primary key."""
        ...

    async def get_by_order_number(self, order_number: str) -> Order | None:
        """Retrieve an order by its human-readable order number."""
        ...

    async def get_by_user_id(
        self, user_id: int, offset: int, limit: int
    ) -> tuple[list[Order], int]:
        """Return paginated orders for a user, ordered by created_at DESC."""
        ...

    async def update_status(self, order_id: int, status: OrderStatus) -> Order:
        """Update the order status and return the updated order."""
        ...

    async def update_payment_status(
        self,
        order_id: int,
        payment_status: PaymentStatus,
        payment_id: str | None = None,
        payment_gateway: str | None = None,
    ) -> Order:
        """Update the payment status and return the updated order."""
        ...

    async def order_number_exists(self, order_number: str) -> bool:
        """Return True if the order number is already taken."""
        ...
