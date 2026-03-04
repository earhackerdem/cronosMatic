import uuid

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
            select(CategoryModel).where(CategoryModel.id == category_id)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_slug(self, slug: str) -> Category | None:
        result = await self.session.execute(
            select(CategoryModel).where(CategoryModel.slug == slug)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_all(self) -> list[Category]:
        result = await self.session.execute(select(CategoryModel))
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]
