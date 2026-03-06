from typing import Protocol

from app.domain.refresh_token.entity import RefreshToken


class RefreshTokenRepositoryInterface(Protocol):
    async def create(self, entity: RefreshToken) -> RefreshToken: ...

    async def get_by_jti(self, jti: str) -> RefreshToken | None: ...

    async def revoke_by_user_id(self, user_id: int) -> None: ...
