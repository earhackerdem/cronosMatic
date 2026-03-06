from decimal import Decimal

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.product.entity import Product, ProductCategory
from app.domain.product.repository import ProductRepositoryInterface
from app.models.product import ProductModel

# Allowed sort columns (whitelist to prevent injection)
_SORT_COLUMN_MAP = {
    "name": ProductModel.name,
    "price": ProductModel.price,
    "created_at": ProductModel.created_at,
    "stock_quantity": ProductModel.stock_quantity,
}


class ProductRepository(ProductRepositoryInterface):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(self, model: ProductModel) -> Product:
        # Eagerly-loaded category relationship populates ProductCategory if present
        cat = None
        try:
            if model.category is not None:
                cat = ProductCategory(
                    id=model.category.id,
                    name=model.category.name,
                    slug=model.category.slug,
                )
        except Exception:
            pass  # relationship not loaded — leave cat as None

        return Product(
            id=model.id,
            category_id=model.category_id,
            name=model.name,
            slug=model.slug,
            sku=model.sku,
            description=model.description,
            price=Decimal(str(model.price)),
            stock_quantity=model.stock_quantity,
            brand=model.brand,
            movement_type=model.movement_type,
            image_path=model.image_path,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            category=cat,
        )

    def _to_model(self, entity: Product) -> ProductModel:
        return ProductModel(
            category_id=entity.category_id,
            name=entity.name,
            slug=entity.slug,
            sku=entity.sku,
            description=entity.description,
            price=entity.price,
            stock_quantity=entity.stock_quantity,
            brand=entity.brand,
            movement_type=entity.movement_type,
            image_path=entity.image_path,
            is_active=entity.is_active,
        )

    async def create(self, product: Product) -> Product:
        model = self._to_model(product)
        self.session.add(model)
        await self.session.commit()
        # Reload with category relationship eagerly loaded
        result = await self.session.execute(
            select(ProductModel)
            .options(selectinload(ProductModel.category))
            .where(ProductModel.id == model.id)
        )
        model = result.scalar_one()
        return self._to_domain(model)

    async def get_by_id(self, product_id: int) -> Product | None:
        result = await self.session.execute(
            select(ProductModel)
            .options(selectinload(ProductModel.category))
            .where(ProductModel.id == product_id)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_slug(self, slug: str) -> Product | None:
        """No active filter — used by admin and slug uniqueness checks."""
        result = await self.session.execute(
            select(ProductModel)
            .options(selectinload(ProductModel.category))
            .where(ProductModel.slug == slug)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_slug_active(self, slug: str) -> Product | None:
        """Returns the product only if it is active."""
        result = await self.session.execute(
            select(ProductModel)
            .options(selectinload(ProductModel.category))
            .where(
                ProductModel.slug == slug,
                ProductModel.is_active.is_(True),
            )
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_sku(self, sku: str) -> Product | None:
        result = await self.session.execute(
            select(ProductModel)
            .options(selectinload(ProductModel.category))
            .where(ProductModel.sku == sku)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_active(
        self,
        offset: int,
        limit: int,
        category_id: int | None,
        search: str | None,
        sort_by: str,
        sort_direction: str,
    ) -> tuple[list[Product], int]:
        # Build base filter
        filters = [ProductModel.is_active.is_(True)]

        if category_id is not None:
            filters.append(ProductModel.category_id == category_id)

        if search:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    ProductModel.name.ilike(pattern),
                    ProductModel.description.ilike(pattern),
                    ProductModel.sku.ilike(pattern),
                )
            )

        # Count query
        count_result = await self.session.execute(
            select(func.count()).select_from(ProductModel).where(*filters)
        )
        total = count_result.scalar_one()

        # Sort column
        sort_col = _SORT_COLUMN_MAP.get(sort_by, ProductModel.name)
        order_fn = desc if sort_direction.lower() == "desc" else asc

        # Data query
        result = await self.session.execute(
            select(ProductModel)
            .options(selectinload(ProductModel.category))
            .where(*filters)
            .order_by(order_fn(sort_col))
            .offset(offset)
            .limit(limit)
        )
        models = result.scalars().all()
        return [self._to_domain(m) for m in models], total

    async def list_all(self, offset: int, limit: int) -> tuple[list[Product], int]:
        count_result = await self.session.execute(select(func.count(ProductModel.id)))
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(ProductModel)
            .options(selectinload(ProductModel.category))
            .offset(offset)
            .limit(limit)
        )
        models = result.scalars().all()
        return [self._to_domain(m) for m in models], total

    async def update(self, product: Product) -> Product:
        result = await self.session.execute(
            select(ProductModel).where(ProductModel.id == product.id)
        )
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Product with id {product.id} not found")

        model.category_id = product.category_id
        model.name = product.name
        model.slug = product.slug
        model.sku = product.sku
        model.description = product.description
        model.price = product.price
        model.stock_quantity = product.stock_quantity
        model.brand = product.brand
        model.movement_type = product.movement_type
        model.image_path = product.image_path
        model.is_active = product.is_active

        await self.session.commit()
        # Reload with category relationship eagerly loaded
        result = await self.session.execute(
            select(ProductModel)
            .options(selectinload(ProductModel.category))
            .where(ProductModel.id == model.id)
        )
        model = result.scalar_one()
        return self._to_domain(model)

    async def delete(self, product_id: int) -> bool:
        result = await self.session.execute(
            select(ProductModel).where(ProductModel.id == product_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return False

        await self.session.delete(model)
        await self.session.commit()
        return True
