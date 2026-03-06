from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user.entity import User
from app.models.user import UserModel


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(self, model: UserModel) -> User:
        return User(
            id=model.id,
            name=model.name,
            email=model.email,
            hashed_password=model.password,
            is_admin=model.is_admin,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: User) -> UserModel:
        return UserModel(
            name=entity.name,
            email=entity.email,
            password=entity.hashed_password,
            is_admin=entity.is_admin,
        )

    async def create(self, entity: User) -> User:
        model = self._to_model(entity)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_domain(model)

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None
