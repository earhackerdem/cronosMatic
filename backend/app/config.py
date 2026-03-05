from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    debug: bool = False
    secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:4200"

    database_url: str = Field(
        default="postgresql+asyncpg://cronosmatic:change-me-in-production@localhost:5432/cronosmatic",
        validation_alias="DATABASE_URL",
        description="Connection string for PostgreSQL. MUST be overridden in production via environment variables.",
    )


    model_config = {"env_prefix": "BACKEND_"}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
