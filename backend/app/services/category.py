import uuid

from sqlalchemy.exc import IntegrityError

from app.domain.category.entity import Category
from app.domain.category.repository import CategoryRepositoryInterface
from app.schemas.category import CategoryUpdate


class CategoryConflictError(ValueError):
    """Raised when a category slug conflicts with an existing one."""


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
        self,
        name_i18n: dict[str, str],
        slug: str,
        description_i18n: dict[str, str] | None = None,
    ) -> Category:
        existing = await self.repository.get_by_slug(slug)
        if existing:
            raise CategoryConflictError(f"Category with slug '{slug}' already exists")
        category = Category(name=name_i18n, slug=slug, description=description_i18n)
        try:
            return await self.repository.create(category)
        except IntegrityError:
            raise CategoryConflictError(f"Category with slug '{slug}' already exists")

    async def update_category(
        self, category_id: uuid.UUID, data: CategoryUpdate
    ) -> Category | None:
        category = await self.repository.get_by_id(category_id)
        if not category:
            return None

        if "slug" in data.model_fields_set and data.slug != category.slug:
            existing = await self.repository.get_by_slug(data.slug)
            if existing:
                raise CategoryConflictError(
                    f"Category with slug '{data.slug}' already exists"
                )
            category.slug = data.slug

        if "name" in data.model_fields_set:
            category.name = data.name
        if "description" in data.model_fields_set:
            category.description = data.description

        try:
            return await self.repository.update(category)
        except ValueError:
            return None
        except IntegrityError:
            raise CategoryConflictError(
                f"Category with slug '{category.slug}' already exists"
            )

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
                raise CategoryConflictError(
                    f"Category with slug '{slug}' already exists"
                )

        category.name = name_i18n
        category.slug = slug
        category.description = description_i18n

        try:
            return await self.repository.update(category)
        except ValueError:
            return None
        except IntegrityError:
            raise CategoryConflictError(f"Category with slug '{slug}' already exists")

    async def delete_category(self, category_id: uuid.UUID) -> bool:
        return await self.repository.soft_delete(category_id)
