import uuid
from typing import Protocol

from app.domain.category.entity import Category


class CategoryRepositoryInterface(Protocol):
    async def create(self, category: Category) -> Category:
        """Persists a new category into the storage."""
        ...

    async def get_by_id(self, category_id: uuid.UUID) -> Category | None:
        """Retrieves a category given its unique ID."""
        ...

    async def get_by_slug(self, slug: str) -> Category | None:
        """Retrieves a category given its unique slug."""
        ...

    async def get_all(self) -> list[Category]:
        """Retrieves all available categories."""
        ...
