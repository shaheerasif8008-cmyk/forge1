from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = Field(default="dev", alias="ENV")
    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    database_url: str = Field(
        default="postgresql://forge:forge@localhost:5432/forge", alias="DATABASE_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    backend_cors_origins: str = Field(default="*", alias="BACKEND_CORS_ORIGINS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


settings = Settings()
