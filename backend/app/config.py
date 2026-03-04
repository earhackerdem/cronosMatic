from pydantic import computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    debug: bool = False
    secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:4200"

    model_config = {"env_prefix": "BACKEND_"}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
