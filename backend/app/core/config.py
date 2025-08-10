from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    project_name: str = Field(default="Forge 1 Backend", alias="PROJECT_NAME")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    # CORS
    backend_cors_origins: str = Field(
        default="*", alias="BACKEND_CORS_ORIGINS"
    )

    # Security
    jwt_secret_key: str = Field(default="change-me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=60 * 24, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # Demo auth stub credentials
    demo_username: str = Field(default="admin", alias="DEMO_USERNAME")
    demo_password: str = Field(default="admin", alias="DEMO_PASSWORD")

    # Datastores
    database_url: str = Field(
        default="postgresql://forge:forge@localhost:5432/forge",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()  # type: ignore[call-arg]


