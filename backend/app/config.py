from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    debug: bool = False
    secret_key: str = "change-me-in-production"
    cors_origins: list[str] = ["http://localhost:4200"]

    model_config = {"env_prefix": "BACKEND_"}


settings = Settings()
