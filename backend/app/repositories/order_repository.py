from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.order.entity import Order, OrderItem, OrderStatus, PaymentStatus
from app.domain.order.repository import OrderRepositoryProtocol
from app.models.order import OrderItemModel, OrderModel
from app.models.product import ProductModel


class OrderRepository(OrderRepositoryProtocol):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ─── Eager-load options ───────────────────────────────────────────────────

    @staticmethod
    def _eager_options():
        return [
            selectinload(OrderModel.items),
            selectinload(OrderModel.shipping_address),
            selectinload(OrderModel.billing_address),
        ]

    # ─── Mapping helpers ──────────────────────────────────────────────────────

    def _to_domain_item(self, model: OrderItemModel) -> OrderItem:
        return OrderItem(
            id=model.id,
            order_id=model.order_id,
            product_id=model.product_id,
            product_name=model.product_name,
            quantity=model.quantity,
            price_per_unit=Decimal(str(model.price_per_unit)),
            total_price=Decimal(str(model.total_price)),
        )

    def _to_domain(self, model: OrderModel) -> Order:
        return Order(
            id=model.id,
            order_number=model.order_number,
            user_id=model.user_id,
            guest_email=model.guest_email,
            status=OrderStatus(model.status),
            payment_status=PaymentStatus(model.payment_status),
            shipping_address_id=model.shipping_address_id,
            billing_address_id=model.billing_address_id,
            subtotal_amount=Decimal(str(model.subtotal_amount)),
            shipping_cost=Decimal(str(model.shipping_cost)),
            total_amount=Decimal(str(model.total_amount)),
            payment_gateway=model.payment_gateway,
            payment_id=model.payment_id,
            shipping_method_name=model.shipping_method_name,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
            items=[self._to_domain_item(item) for item in model.items],
        )

    # ─── Interface implementation ─────────────────────────────────────────────

    async def create(self, order: Order) -> Order:
        """Flush only — the service manages the transaction boundary."""
        model = OrderModel(
            order_number=order.order_number,
            user_id=order.user_id,
            guest_email=order.guest_email,
            status=order.status.value,
            payment_status=order.payment_status.value,
            shipping_address_id=order.shipping_address_id,
            billing_address_id=order.billing_address_id,
            subtotal_amount=order.subtotal_amount,
            shipping_cost=order.shipping_cost,
            total_amount=order.total_amount,
            payment_gateway=order.payment_gateway,
            payment_id=order.payment_id,
            shipping_method_name=order.shipping_method_name,
            notes=order.notes,
        )
        self.session.add(model)
        await self.session.flush()

        # Create order items
        for item in order.items:
            item_model = OrderItemModel(
                order_id=model.id,
                product_id=item.product_id,
                product_name=item.product_name,
                quantity=item.quantity,
                price_per_unit=item.price_per_unit,
                total_price=item.total_price,
            )
            self.session.add(item_model)

        await self.session.flush()
        # Return a minimal domain object; caller will reload after commit
        order.id = model.id
        return order

    async def get_by_id(self, order_id: int) -> Order | None:
        result = await self.session.execute(
            select(OrderModel)
            .options(*self._eager_options())
            .where(OrderModel.id == order_id)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_order_number(self, order_number: str) -> Order | None:
        result = await self.session.execute(
            select(OrderModel)
            .options(*self._eager_options())
            .where(OrderModel.order_number == order_number)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_user_id(
        self, user_id: int, offset: int, limit: int
    ) -> tuple[list[Order], int]:
        # Count query
        count_result = await self.session.execute(
            select(func.count())
            .select_from(OrderModel)
            .where(OrderModel.user_id == user_id)
        )
        total = count_result.scalar_one()

        # Data query
        result = await self.session.execute(
            select(OrderModel)
            .options(*self._eager_options())
            .where(OrderModel.user_id == user_id)
            .order_by(OrderModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        models = result.scalars().all()
        return [self._to_domain(m) for m in models], total

    async def update_status(self, order_id: int, status: OrderStatus) -> Order:
        result = await self.session.execute(
            select(OrderModel)
            .options(*self._eager_options())
            .where(OrderModel.id == order_id)
        )
        model = result.scalar_one()
        model.status = status.value
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_domain(model)

    async def update_payment_status(
        self,
        order_id: int,
        payment_status: PaymentStatus,
        payment_id: str | None = None,
        payment_gateway: str | None = None,
    ) -> Order:
        result = await self.session.execute(
            select(OrderModel)
            .options(*self._eager_options())
            .where(OrderModel.id == order_id)
        )
        model = result.scalar_one()
        model.payment_status = payment_status.value
        if payment_id is not None:
            model.payment_id = payment_id
        if payment_gateway is not None:
            model.payment_gateway = payment_gateway
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_domain(model)

    async def order_number_exists(self, order_number: str) -> bool:
        result = await self.session.execute(
            select(func.count())
            .select_from(OrderModel)
            .where(OrderModel.order_number == order_number)
        )
        return result.scalar_one() > 0

    async def lock_and_get_products(self, product_ids: list[int]) -> list[ProductModel]:
        """Lock products FOR UPDATE and return raw ProductModel instances."""
        result = await self.session.execute(
            select(ProductModel)
            .where(ProductModel.id.in_(product_ids))
            .with_for_update()
        )
        return list(result.scalars().all())
