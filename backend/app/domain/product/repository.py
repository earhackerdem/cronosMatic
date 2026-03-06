from typing import Protocol

from app.domain.product.entity import Product


class ProductRepositoryInterface(Protocol):
    async def create(self, product: Product) -> Product:
        """Persists a new product into the storage."""
        ...

    async def get_by_id(self, product_id: int) -> Product | None:
        """Retrieves a product given its unique integer ID."""
        ...

    async def get_by_slug(self, slug: str) -> Product | None:
        """Retrieves a product given its slug (no active filter — used by admin)."""
        ...

    async def get_by_slug_active(self, slug: str) -> Product | None:
        """Retrieves an active product given its slug."""
        ...

    async def get_by_sku(self, sku: str) -> Product | None:
        """Retrieves a product given its SKU."""
        ...

    async def list_active(
        self,
        offset: int,
        limit: int,
        category_id: int | None,
        search: str | None,
        sort_by: str,
        sort_direction: str,
    ) -> tuple[list[Product], int]:
        """Returns active products with total count, supporting filters."""
        ...

    async def list_all(
        self, offset: int, limit: int
    ) -> tuple[list[Product], int]:
        """Returns all products (admin, no filter) with total count."""
        ...

    async def update(self, product: Product) -> Product:
        """Updates an existing product in the storage."""
        ...

    async def delete(self, product_id: int) -> bool:
        """Hard deletes a product. Returns True if found, False otherwise."""
        ...
