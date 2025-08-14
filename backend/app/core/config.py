from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = Field(default="dev", alias="ENV")
    # JWT secret may be None in dev; startup validation enforces presence in prod
    jwt_secret: str | None = Field(default=None, alias="JWT_SECRET")
    database_url: str = Field(
        default="postgresql://forge:forge@localhost:5432/forge", alias="DATABASE_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    backend_cors_origins: str = Field(default="*", alias="BACKEND_CORS_ORIGINS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Employee Keys / Export
    employee_key_pepper: str | None = Field(default=None, alias="EMPLOYEE_KEY_PEPPER")
    export_signing_secret: str | None = Field(default=None, alias="EXPORT_SIGNING_SECRET")
    # LLM/OpenRouter live-mode configuration
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    max_tokens_per_req: int = Field(default=2048, alias="MAX_TOKENS_PER_REQ")
    llm_timeout_secs: float = Field(default=45.0, alias="LLM_TIMEOUT_SECS")
    # Feedback loop & retries
    feedback_max_retries: int = Field(default=1, alias="FEEDBACK_MAX_RETRIES")
    retry_score_threshold: float = Field(default=0.55, alias="RETRY_SCORE_THRESHOLD")
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    db_pool_recycle: int = Field(default=1800, alias="DB_POOL_RECYCLE")

    # Optional global daily token cap for employees (can be overridden per-employee)
    employee_daily_tokens_cap: int | None = Field(default=None, alias="EMPLOYEE_DAILY_TOKENS_CAP")

    # Circuit breaker configuration for outbound LLM calls
    circuit_breaker_threshold: int = Field(default=3, alias="CIRCUIT_BREAKER_THRESHOLD")
    circuit_breaker_cooldown_secs: int = Field(default=60, alias="CIRCUIT_BREAKER_COOLDOWN_SECS")

    # Auth/email configuration
    jwt_refresh_secret: str | None = Field(default=None, alias="JWT_REFRESH_SECRET")
    access_token_ttl_minutes: int = Field(default=60, alias="ACCESS_TOKEN_TTL_MINUTES")
    refresh_token_ttl_days: int = Field(default=30, alias="REFRESH_TOKEN_TTL_DAYS")
    resend_api_key: str | None = Field(default=None, alias="RESEND_API_KEY")
    frontend_base_url: str = Field(default="http://localhost:5173", alias="FRONTEND_BASE_URL")
    auth_v2_enabled: bool = Field(default=True, alias="AUTH_V2_ENABLED")
    # Brute-force protection (per IP and per email)
    login_rate_limit_per_minute: int = Field(default=5, alias="LOGIN_RATE_LIMIT_PER_MINUTE")

    # Interconnect / AI Comms features
    interconnect_enabled: bool = Field(default=True, alias="INTERCONNECT_ENABLED")
    ai_comms_dashboard_enabled: bool = Field(default=True, alias="AI_COMMS_DASHBOARD_ENABLED")


settings = Settings()
