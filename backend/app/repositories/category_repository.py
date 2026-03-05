import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.category.entity import Category
from app.domain.category.repository import CategoryRepositoryInterface
from app.models.category import CategoryModel


class CategoryRepository(CategoryRepositoryInterface):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(self, model: CategoryModel) -> Category:
        return Category(
            id=model.id,
            slug=model.slug,
            name=model.name,
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: Category) -> CategoryModel:
        return CategoryModel(
            id=entity.id,
            slug=entity.slug,
            name=entity.name,
            description=entity.description,
        )

    async def create(self, category: Category) -> Category:
        category_model = self._to_model(category)
        self.session.add(category_model)
        await self.session.commit()
        await self.session.refresh(category_model)
        return self._to_domain(category_model)

    async def get_by_id(self, category_id: uuid.UUID) -> Category | None:
        result = await self.session.execute(
            select(CategoryModel).where(
                CategoryModel.id == category_id,
                CategoryModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_slug(self, slug: str) -> Category | None:
        result = await self.session.execute(
            select(CategoryModel).where(
                CategoryModel.slug == slug,
                CategoryModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_all(self) -> list[Category]:
        result = await self.session.execute(
            select(CategoryModel).where(CategoryModel.deleted_at.is_(None))
        )
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]

    async def update(self, category: Category) -> Category:
        result = await self.session.execute(
            select(CategoryModel).where(
                CategoryModel.id == category.id,
                CategoryModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Category with id {category.id} not found")

        model.name = category.name
        model.slug = category.slug
        model.description = category.description

        await self.session.commit()
        await self.session.refresh(model)
        return self._to_domain(model)

    async def soft_delete(self, category_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(CategoryModel).where(
                CategoryModel.id == category_id,
                CategoryModel.deleted_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            return False

        model.deleted_at = datetime.now(timezone.utc)
        await self.session.commit()
        return True
