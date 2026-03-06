import re

from app.domain.category.repository import CategoryRepositoryInterface
from app.domain.product.entity import Product
from app.domain.product.repository import ProductRepositoryInterface


class ProductConflictError(ValueError):
    """Raised when a product slug or SKU conflicts with an existing one."""


class ProductCategoryNotFoundError(ValueError):
    """Raised when the specified category does not exist or is inactive."""


class ProductNotFoundError(ValueError):
    """Raised when a product is not found."""


class ProductService:
    def __init__(
        self,
        repository: ProductRepositoryInterface,
        category_repository: CategoryRepositoryInterface,
    ):
        self.repository = repository
        self.category_repository = category_repository

    def _generate_slug(self, name: str) -> str:
        """Generate a URL-friendly slug from a product name."""
        slug = name.lower().strip()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s-]+", "-", slug)
        return slug.strip("-")

    async def list_active(
        self,
        page: int,
        size: int,
        category_slug: str | None,
        search: str | None,
        sort_by: str,
        sort_direction: str,
    ) -> tuple[list[Product], int]:
        offset = (page - 1) * size
        category_id = None

        if category_slug is not None:
            category = await self.category_repository.get_by_slug_active(category_slug)
            if not category:
                raise ProductCategoryNotFoundError(
                    f"Category with slug '{category_slug}' not found."
                )
            category_id = category.id

        return await self.repository.list_active(
            offset=offset,
            limit=size,
            category_id=category_id,
            search=search,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

    async def list_all_admin(self, page: int, size: int) -> tuple[list[Product], int]:
        offset = (page - 1) * size
        return await self.repository.list_all(offset=offset, limit=size)

    async def get_active_by_slug(self, slug: str) -> Product | None:
        return await self.repository.get_by_slug_active(slug)

    async def get_by_id(self, product_id: int) -> Product | None:
        return await self.repository.get_by_id(product_id)

    async def create_product(self, data: dict) -> Product:
        category_id = data.get("category_id")
        category = await self.category_repository.get_by_id(category_id)
        if not category:
            raise ProductCategoryNotFoundError(
                f"Category with id '{category_id}' not found."
            )

        # Generate or use provided slug
        slug = data.get("slug") or self._generate_slug(data["name"])

        # Check slug uniqueness
        existing_slug = await self.repository.get_by_slug(slug)
        if existing_slug:
            raise ProductConflictError(f"Product with slug '{slug}' already exists.")

        # Check SKU uniqueness
        sku = data["sku"]
        existing_sku = await self.repository.get_by_sku(sku)
        if existing_sku:
            raise ProductConflictError(f"Product with SKU '{sku}' already exists.")

        product = Product(
            category_id=category_id,
            name=data["name"],
            slug=slug,
            sku=sku,
            description=data.get("description"),
            price=data["price"],
            stock_quantity=data.get("stock_quantity", 0),
            brand=data.get("brand"),
            movement_type=data.get("movement_type"),
            image_path=data.get("image_path"),
            is_active=data.get("is_active", True),
        )
        return await self.repository.create(product)

    async def update_product(self, product_id: int, data: dict) -> Product | None:
        product = await self.repository.get_by_id(product_id)
        if not product:
            return None

        # Validate new category if being changed
        if "category_id" in data:
            category = await self.category_repository.get_by_id(data["category_id"])
            if not category:
                raise ProductCategoryNotFoundError(
                    f"Category with id '{data['category_id']}' not found."
                )

        # Validate slug uniqueness if slug is changing
        if "slug" in data and data["slug"] != product.slug:
            existing = await self.repository.get_by_slug(data["slug"])
            if existing and existing.id != product_id:
                raise ProductConflictError(
                    f"Product with slug '{data['slug']}' already exists."
                )

        # Validate SKU uniqueness if SKU is changing
        if "sku" in data and data["sku"] != product.sku:
            existing = await self.repository.get_by_sku(data["sku"])
            if existing and existing.id != product_id:
                raise ProductConflictError(
                    f"Product with SKU '{data['sku']}' already exists."
                )

        # Apply only the fields that were provided
        updatable_fields = (
            "category_id",
            "name",
            "slug",
            "sku",
            "description",
            "price",
            "stock_quantity",
            "brand",
            "movement_type",
            "image_path",
            "is_active",
        )
        for field_name in updatable_fields:
            if field_name in data:
                setattr(product, field_name, data[field_name])

        return await self.repository.update(product)

    async def delete_product(self, product_id: int) -> bool:
        return await self.repository.delete(product_id)
