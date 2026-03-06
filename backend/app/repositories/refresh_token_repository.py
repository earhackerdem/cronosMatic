from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.refresh_token.entity import RefreshToken
from app.models.refresh_token import RefreshTokenModel


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(self, model: RefreshTokenModel) -> RefreshToken:
        return RefreshToken(
            id=model.id,
            user_id=model.user_id,
            token_jti=model.token_jti,
            expires_at=model.expires_at,
            revoked_at=model.revoked_at,
            created_at=model.created_at,
        )

    def _to_model(self, entity: RefreshToken) -> RefreshTokenModel:
        return RefreshTokenModel(
            user_id=entity.user_id,
            token_jti=entity.token_jti,
            expires_at=entity.expires_at,
        )

    async def create(self, entity: RefreshToken) -> RefreshToken:
        model = self._to_model(entity)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_domain(model)

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_jti == jti)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def revoke_by_user_id(self, user_id: int) -> None:
        result = await self.session.execute(
            select(RefreshTokenModel).where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.revoked_at.is_(None),
            )
        )
        models = result.scalars().all()
        now = datetime.now(timezone.utc)
        for model in models:
            model.revoked_at = now
        await self.session.commit()
