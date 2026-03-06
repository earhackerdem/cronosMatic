from sqlalchemy.exc import IntegrityError

from app.domain.category.entity import Category
from app.domain.category.repository import CategoryRepositoryInterface


class CategoryConflictError(ValueError):
    """Raised when a category slug conflicts with an existing one."""


class CategoryService:
    def __init__(self, repository: CategoryRepositoryInterface):
        self.repository = repository

    async def list_active(self, page: int, size: int) -> tuple[list[Category], int]:
        offset = (page - 1) * size
        return await self.repository.list_active(offset=offset, limit=size)

    async def list_all_admin(self, page: int, size: int) -> tuple[list[Category], int]:
        offset = (page - 1) * size
        return await self.repository.list_all(offset=offset, limit=size)

    async def get_active_by_slug(self, slug: str) -> Category | None:
        return await self.repository.get_by_slug_active(slug)

    async def get_by_id(self, category_id: int) -> Category | None:
        return await self.repository.get_by_id(category_id)

    async def create_category(
        self,
        name: str,
        slug: str,
        description: str | None = None,
        image_path: str | None = None,
        is_active: bool = True,
    ) -> Category:
        existing = await self.repository.get_by_slug(slug)
        if existing:
            raise CategoryConflictError(f"Category with slug '{slug}' already exists")
        category = Category(
            name=name,
            slug=slug,
            description=description,
            image_path=image_path,
            is_active=is_active,
        )
        try:
            return await self.repository.create(category)
        except IntegrityError:
            raise CategoryConflictError(f"Category with slug '{slug}' already exists")

    async def update_category(self, category_id: int, data: dict) -> Category | None:
        category = await self.repository.get_by_id(category_id)
        if not category:
            return None

        # Handle slug uniqueness check only if slug is changing
        if "slug" in data and data["slug"] != category.slug:
            existing = await self.repository.get_by_slug(data["slug"])
            if existing:
                raise CategoryConflictError(
                    f"Category with slug '{data['slug']}' already exists"
                )

        # Apply only the fields that were provided
        for field_name in ("name", "slug", "description", "image_path", "is_active"):
            if field_name in data:
                setattr(category, field_name, data[field_name])

        try:
            return await self.repository.update(category)
        except IntegrityError:
            raise CategoryConflictError(
                f"Category with slug '{category.slug}' already exists"
            )

    async def delete_category(self, category_id: int) -> bool:
        return await self.repository.set_inactive(category_id)
