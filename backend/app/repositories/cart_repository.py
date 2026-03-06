from decimal import Decimal

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.cart.entity import Cart, CartItem, CartItemProduct
from app.domain.cart.repository import CartRepositoryInterface
from app.models.cart import CartItemModel, CartModel


class CartRepository(CartRepositoryInterface):
    def __init__(self, session: AsyncSession):
        self.session = session

    # ─── Mapping helpers ─────────────────────────────────────────────────────

    def _to_domain_item(self, model: CartItemModel) -> CartItem:
        product_embed = None
        try:
            if model.product is not None:
                product_embed = CartItemProduct(
                    id=model.product.id,
                    name=model.product.name,
                    slug=model.product.slug,
                    price=Decimal(str(model.product.price)),
                    stock_quantity=model.product.stock_quantity,
                    image_path=model.product.image_path,
                )
        except Exception:
            pass  # relationship not loaded — leave product_embed as None

        return CartItem(
            id=model.id,
            cart_id=model.cart_id,
            product_id=model.product_id,
            quantity=model.quantity,
            unit_price=Decimal(str(model.unit_price)),
            total_price=Decimal(str(model.total_price)),
            product=product_embed,
        )

    def _to_domain(self, model: CartModel) -> Cart:
        items = [self._to_domain_item(item) for item in model.items]
        return Cart(
            id=model.id,
            user_id=model.user_id,
            session_id=model.session_id,
            total_items=model.total_items,
            total_amount=Decimal(str(model.total_amount)),
            expires_at=model.expires_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            items=items,
        )

    # ─── Eager-load query options ─────────────────────────────────────────────

    @staticmethod
    def _eager_options():
        return selectinload(CartModel.items).selectinload(CartItemModel.product)

    # ─── Active cart filter ───────────────────────────────────────────────────

    @staticmethod
    def _active_filter():
        """Returns filter condition: expires_at IS NULL OR expires_at > now()."""
        return or_(CartModel.expires_at.is_(None), CartModel.expires_at > func.now())

    # ─── Reload helper ────────────────────────────────────────────────────────

    async def _reload(self, cart_id: int) -> Cart:
        result = await self.session.execute(
            select(CartModel)
            .options(CartRepository._eager_options())
            .where(CartModel.id == cart_id)
        )
        model = result.scalar_one()
        return self._to_domain(model)

    # ─── Interface implementation ─────────────────────────────────────────────

    async def get_by_user_id(self, user_id: int) -> Cart | None:
        result = await self.session.execute(
            select(CartModel)
            .options(CartRepository._eager_options())
            .where(CartModel.user_id == user_id, CartRepository._active_filter())
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_session_id(self, session_id: str) -> Cart | None:
        result = await self.session.execute(
            select(CartModel)
            .options(CartRepository._eager_options())
            .where(
                CartModel.session_id == session_id,
                CartRepository._active_filter(),
            )
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def create(self, cart: Cart) -> Cart:
        model = CartModel(
            user_id=cart.user_id,
            session_id=cart.session_id,
            total_items=cart.total_items,
            total_amount=cart.total_amount,
            expires_at=cart.expires_at,
        )
        self.session.add(model)
        await self.session.commit()
        return await self._reload(model.id)

    async def save(self, cart: Cart) -> Cart:
        result = await self.session.execute(
            select(CartModel).where(CartModel.id == cart.id)
        )
        model = result.scalar_one()
        model.total_items = cart.total_items
        model.total_amount = cart.total_amount
        await self.session.commit()
        return await self._reload(cart.id)

    async def get_item_by_id(self, cart_item_id: int) -> CartItem | None:
        result = await self.session.execute(
            select(CartItemModel)
            .options(selectinload(CartItemModel.product))
            .where(CartItemModel.id == cart_item_id)
        )
        model = result.scalar_one_or_none()
        return self._to_domain_item(model) if model else None

    async def add_item(
        self,
        cart_id: int,
        product_id: int,
        quantity: int,
        unit_price: Decimal,
    ) -> CartItem:
        total_price = quantity * unit_price
        model = CartItemModel(
            cart_id=cart_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
        )
        self.session.add(model)
        await self.session.commit()
        # Reload with product eager loaded
        result = await self.session.execute(
            select(CartItemModel)
            .options(selectinload(CartItemModel.product))
            .where(CartItemModel.id == model.id)
        )
        model = result.scalar_one()
        return self._to_domain_item(model)

    async def update_item(
        self,
        cart_item_id: int,
        quantity: int,
        unit_price: Decimal,
    ) -> CartItem:
        result = await self.session.execute(
            select(CartItemModel).where(CartItemModel.id == cart_item_id)
        )
        model = result.scalar_one()
        model.quantity = quantity
        model.unit_price = unit_price
        model.total_price = quantity * unit_price
        await self.session.commit()
        # Reload with product
        result = await self.session.execute(
            select(CartItemModel)
            .options(selectinload(CartItemModel.product))
            .where(CartItemModel.id == cart_item_id)
        )
        model = result.scalar_one()
        return self._to_domain_item(model)

    async def delete_item(self, cart_item_id: int) -> None:
        result = await self.session.execute(
            select(CartItemModel).where(CartItemModel.id == cart_item_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            await self.session.commit()

    async def clear_items(self, cart_id: int) -> None:
        await self.session.execute(
            delete(CartItemModel).where(CartItemModel.cart_id == cart_id)
        )
        await self.session.commit()

    async def delete_cart(self, cart_id: int) -> None:
        result = await self.session.execute(
            select(CartModel).where(CartModel.id == cart_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            await self.session.commit()
