from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt as _bcrypt
from jose import JWTError, jwt

from app.config import Settings
from app.domain.refresh_token.entity import RefreshToken
from app.domain.refresh_token.repository import RefreshTokenRepositoryInterface
from app.domain.user.entity import User
from app.domain.user.repository import UserRepositoryInterface


class UserConflictError(ValueError):
    """Raised when a user with the given email already exists."""


class InvalidCredentialsError(ValueError):
    """Raised when authentication credentials are invalid."""


class InvalidTokenError(ValueError):
    """Raised when a JWT token is invalid, expired, or revoked."""


ALGORITHM = "HS256"


class AuthService:
    def __init__(
        self,
        user_repo: UserRepositoryInterface,
        refresh_token_repo: RefreshTokenRepositoryInterface,
        settings: Settings,
    ):
        self.user_repo = user_repo
        self.refresh_token_repo = refresh_token_repo
        self.settings = settings

    # ─── Password helpers ────────────────────────────────────────────────────

    def hash_password(self, password: str) -> str:
        salt = _bcrypt.gensalt()
        return _bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, plain: str, hashed: str) -> bool:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

    # ─── Token helpers ───────────────────────────────────────────────────────

    def create_access_token(self, user: User) -> str:
        expires_delta = timedelta(minutes=self.settings.jwt_access_token_expire_minutes)
        expire = datetime.now(timezone.utc) + expires_delta
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "is_admin": user.is_admin,
            "type": "access",
            "exp": expire,
        }
        return jwt.encode(payload, self.settings.jwt_secret_key, algorithm=ALGORITHM)

    def create_refresh_token(self, user: User) -> tuple[str, str]:
        jti = str(uuid4())
        expires_delta = timedelta(days=self.settings.jwt_refresh_token_expire_days)
        expire = datetime.now(timezone.utc) + expires_delta
        payload = {
            "sub": str(user.id),
            "type": "refresh",
            "jti": jti,
            "exp": expire,
        }
        token_str = jwt.encode(
            payload, self.settings.jwt_secret_key, algorithm=ALGORITHM
        )
        return token_str, jti

    def decode_access_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token, self.settings.jwt_secret_key, algorithms=[ALGORITHM]
            )
        except JWTError:
            raise InvalidTokenError("Invalid or expired access token.")
        if payload.get("type") != "access":
            raise InvalidTokenError("Token is not an access token.")
        # Convert sub back to int for consistency
        payload["sub"] = int(payload["sub"])
        return payload

    # ─── Business methods ────────────────────────────────────────────────────

    async def register(
        self, name: str, email: str, password: str
    ) -> tuple[User, str, str]:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise UserConflictError(f"A user with email '{email}' already exists.")

        hashed = self.hash_password(password)
        user = User(name=name, email=email, hashed_password=hashed)
        created_user = await self.user_repo.create(user)

        access_token = self.create_access_token(created_user)
        refresh_token_str, jti = self.create_refresh_token(created_user)

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=self.settings.jwt_refresh_token_expire_days
        )
        rt_entity = RefreshToken(
            user_id=created_user.id,
            token_jti=jti,
            expires_at=expires_at,
        )
        await self.refresh_token_repo.create(rt_entity)

        return created_user, access_token, refresh_token_str

    async def login(self, email: str, password: str) -> tuple[User, str, str]:
        user = await self.user_repo.get_by_email(email)
        if not user or not self.verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("The provided credentials are incorrect.")

        await self.refresh_token_repo.revoke_by_user_id(user.id)

        access_token = self.create_access_token(user)
        refresh_token_str, jti = self.create_refresh_token(user)

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=self.settings.jwt_refresh_token_expire_days
        )
        rt_entity = RefreshToken(
            user_id=user.id,
            token_jti=jti,
            expires_at=expires_at,
        )
        await self.refresh_token_repo.create(rt_entity)

        return user, access_token, refresh_token_str

    async def refresh(self, refresh_token_str: str) -> str:
        try:
            payload = jwt.decode(
                refresh_token_str, self.settings.jwt_secret_key, algorithms=[ALGORITHM]
            )
        except JWTError:
            raise InvalidTokenError("Invalid or expired refresh token.")

        if payload.get("type") != "refresh":
            raise InvalidTokenError("Token is not a refresh token.")

        jti = payload.get("jti")
        if not jti:
            raise InvalidTokenError("Refresh token missing JTI claim.")

        rt_record = await self.refresh_token_repo.get_by_jti(jti)
        if not rt_record:
            raise InvalidTokenError("Refresh token not found.")
        if rt_record.revoked_at is not None:
            raise InvalidTokenError("Refresh token has been revoked.")

        now = datetime.now(timezone.utc)
        expires_at = rt_record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            raise InvalidTokenError("Refresh token has expired.")

        user = await self.user_repo.get_by_id(int(payload["sub"]))
        if not user:
            raise InvalidTokenError("User not found.")

        return self.create_access_token(user)

    async def logout(self, user_id: int) -> None:
        await self.refresh_token_repo.revoke_by_user_id(user_id)
