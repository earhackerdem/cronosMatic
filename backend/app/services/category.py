import uuid

from app.domain.category.entity import Category
from app.domain.category.repository import CategoryRepositoryInterface


class CategoryService:
    def __init__(self, repository: CategoryRepositoryInterface):
        # We depend on an Interface/Protocol, NOT a concrete class! (Clean Architecture/DDD)
        self.repository = repository

    async def get_all_categories(self) -> list[Category]:
        return await self.repository.get_all()

    async def get_category(self, category_id: uuid.UUID) -> Category | None:
        return await self.repository.get_by_id(category_id)

    async def get_category_by_slug(self, slug: str) -> Category | None:
        return await self.repository.get_by_slug(slug)

    async def create_category(
        self, name_i18n: dict[str, str], slug: str, description_i18n: dict[str, str] | None = None
    ) -> Category:
        category = Category(name=name_i18n, slug=slug, description=description_i18n)
        return await self.repository.create(category)
