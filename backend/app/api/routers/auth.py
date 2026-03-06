from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.db.engine import get_db_session
from app.domain.user.entity import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    AuthResponse,
    AuthStatusResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import AuthService, InvalidCredentialsError, InvalidTokenError, UserConflictError

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    user_repo = UserRepository(session)
    rt_repo = RefreshTokenRepository(session)
    return AuthService(user_repo, rt_repo, settings)


@router.post("/register", status_code=201, response_model=AuthResponse)
async def register(
    body: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        user, access_token, refresh_token = await auth_service.register(
            name=body.name,
            email=str(body.email),
            password=body.password,
        )
    except UserConflictError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", status_code=200, response_model=AuthResponse)
async def login(
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        user, access_token, refresh_token = await auth_service.login(
            email=str(body.email),
            password=body.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", status_code=200, response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        access_token = await auth_service.refresh(body.refresh_token)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    return TokenResponse(access_token=access_token)


@router.post("/logout", status_code=204)
async def logout(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    await auth_service.logout(user_id=current_user.id)
    return Response(status_code=204)


# auth-status is registered at the top-level (not under /auth prefix)
auth_status_router = APIRouter(tags=["auth"])


@auth_status_router.get("/auth-status", status_code=200, response_model=AuthStatusResponse)
async def auth_status(current_user: User = Depends(get_current_user)):
    return AuthStatusResponse(
        status="authenticated",
        message="User is authenticated.",
        user=UserResponse.model_validate(current_user),
        timestamp=datetime.now(timezone.utc),
    )
