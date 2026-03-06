from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    debug: bool = False
    secret_key: str = Field(
        description="Secret key for signing. Set via BACKEND_SECRET_KEY."
    )
    cors_origins: str = (
        "http://localhost:5173,http://localhost:4200"  # 5173=Vite, 4200=legacy fallback
    )

    jwt_secret_key: str = Field(
        description="Secret key for JWT signing. Set via BACKEND_JWT_SECRET_KEY."
    )
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    storage_base_url: str = Field(
        default="",
        description="Base URL for S3/storage assets. Set via BACKEND_STORAGE_BASE_URL.",
    )

    database_url: str = Field(
        validation_alias="DATABASE_URL",
        description="PostgreSQL connection string. Set via DATABASE_URL env var.",
    )

    model_config = {"env_prefix": "BACKEND_"}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
