from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.engine import get_db_session
from app.domain.user.entity import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.auth import AuthService, InvalidTokenError


def _make_auth_service(session: AsyncSession) -> AuthService:
    user_repo = UserRepository(session)
    rt_repo = RefreshTokenRepository(session)
    return AuthService(user_repo, rt_repo, settings)


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is required.")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header.")

    token = authorization.removeprefix("Bearer ")
    auth_service = _make_auth_service(session)

    try:
        payload = auth_service.decode_access_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    user_id = payload["sub"]
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


async def get_current_user_optional(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> User | None:
    if not authorization:
        return None
    try:
        return await get_current_user(authorization=authorization, session=session)
    except HTTPException:
        return None


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=403, detail="Forbidden. User is not an administrator."
        )
    return user
