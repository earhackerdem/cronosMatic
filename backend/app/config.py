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
