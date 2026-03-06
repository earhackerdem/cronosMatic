from typing import Protocol

from app.domain.category.entity import Category


class CategoryRepositoryInterface(Protocol):
    async def create(self, category: Category) -> Category:
        """Persists a new category into the storage."""
        ...

    async def get_by_id(self, category_id: int) -> Category | None:
        """Retrieves a category given its unique integer ID."""
        ...

    async def get_by_slug(self, slug: str) -> Category | None:
        """Retrieves a category given its slug (no active filter — used by admin)."""
        ...

    async def get_by_slug_active(self, slug: str) -> Category | None:
        """Retrieves an active category given its slug."""
        ...

    async def list_active(
        self, offset: int, limit: int
    ) -> tuple[list[Category], int]:
        """Returns active categories with total count."""
        ...

    async def list_all(
        self, offset: int, limit: int
    ) -> tuple[list[Category], int]:
        """Returns all categories (admin, no filter) with total count."""
        ...

    async def update(self, category: Category) -> Category:
        """Updates an existing category in the storage."""
        ...

    async def set_inactive(self, category_id: int) -> bool:
        """Sets is_active=False for a category. Returns True if found, False otherwise."""
        ...
