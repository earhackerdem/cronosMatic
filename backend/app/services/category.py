import uuid

from app.domain.category.entity import Category
from app.domain.category.repository import CategoryRepositoryInterface
from app.schemas.category import CategoryUpdate


class CategoryService:
    def __init__(self, repository: CategoryRepositoryInterface):
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
        existing = await self.repository.get_by_slug(slug)
        if existing:
            raise ValueError(f"Category with slug '{slug}' already exists")
        category = Category(name=name_i18n, slug=slug, description=description_i18n)
        return await self.repository.create(category)

    async def update_category(
        self, category_id: uuid.UUID, data: CategoryUpdate
    ) -> Category | None:
        category = await self.repository.get_by_id(category_id)
        if not category:
            return None

        if data.slug is not None and data.slug != category.slug:
            existing = await self.repository.get_by_slug(data.slug)
            if existing:
                raise ValueError(f"Category with slug '{data.slug}' already exists")
            category.slug = data.slug

        if data.name is not None:
            category.name = data.name
        if data.description is not None:
            category.description = data.description

        return await self.repository.update(category)

    async def replace_category(
        self,
        category_id: uuid.UUID,
        name_i18n: dict[str, str],
        slug: str,
        description_i18n: dict[str, str] | None = None,
    ) -> Category | None:
        category = await self.repository.get_by_id(category_id)
        if not category:
            return None

        if slug != category.slug:
            existing = await self.repository.get_by_slug(slug)
            if existing:
                raise ValueError(f"Category with slug '{slug}' already exists")

        category.name = name_i18n
        category.slug = slug
        category.description = description_i18n

        return await self.repository.update(category)

    async def delete_category(self, category_id: uuid.UUID) -> bool:
        return await self.repository.soft_delete(category_id)
