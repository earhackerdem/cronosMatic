from sqlalchemy import func, select
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
            name=model.name,
            slug=model.slug,
            description=model.description,
            image_path=model.image_path,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Category) -> CategoryModel:
        return CategoryModel(
            name=entity.name,
            slug=entity.slug,
            description=entity.description,
            image_path=entity.image_path,
            is_active=entity.is_active,
        )

    async def create(self, category: Category) -> Category:
        model = self._to_model(category)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_domain(model)

    async def get_by_id(self, category_id: int) -> Category | None:
        result = await self.session.execute(
            select(CategoryModel).where(CategoryModel.id == category_id)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_slug(self, slug: str) -> Category | None:
        """No active filter — used by admin and slug uniqueness checks."""
        result = await self.session.execute(
            select(CategoryModel).where(CategoryModel.slug == slug)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_slug_active(self, slug: str) -> Category | None:
        """Returns the category only if it is active."""
        result = await self.session.execute(
            select(CategoryModel).where(
                CategoryModel.slug == slug,
                CategoryModel.is_active.is_(True),
            )
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_active(
        self, offset: int, limit: int
    ) -> tuple[list[Category], int]:
        count_result = await self.session.execute(
            select(func.count()).where(CategoryModel.is_active.is_(True))
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(CategoryModel)
            .where(CategoryModel.is_active.is_(True))
            .offset(offset)
            .limit(limit)
        )
        models = result.scalars().all()
        return [self._to_domain(m) for m in models], total

    async def list_all(
        self, offset: int, limit: int
    ) -> tuple[list[Category], int]:
        count_result = await self.session.execute(select(func.count(CategoryModel.id)))
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(CategoryModel).offset(offset).limit(limit)
        )
        models = result.scalars().all()
        return [self._to_domain(m) for m in models], total

    async def update(self, category: Category) -> Category:
        result = await self.session.execute(
            select(CategoryModel).where(CategoryModel.id == category.id)
        )
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Category with id {category.id} not found")

        model.name = category.name
        model.slug = category.slug
        model.description = category.description
        model.image_path = category.image_path
        model.is_active = category.is_active

        await self.session.commit()
        await self.session.refresh(model)
        return self._to_domain(model)

    async def set_inactive(self, category_id: int) -> bool:
        result = await self.session.execute(
            select(CategoryModel).where(CategoryModel.id == category_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return False

        model.is_active = False
        await self.session.commit()
        return True
