from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="ai-soc", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field(..., alias="REDIS_URL")
    secret_key: str = Field(..., alias="SECRET_KEY")
    llm_provider: str = Field(default="disabled", alias="LLM_PROVIDER")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    brute_force_threshold: int = Field(default=10, alias="BRUTE_FORCE_THRESHOLD")
    brute_force_window_seconds: int = Field(default=60, alias="BRUTE_FORCE_WINDOW_SECONDS")
    password_spray_unique_users: int = Field(default=5, alias="PASSWORD_SPRAY_UNIQUE_USERS")
    password_spray_window_seconds: int = Field(default=300, alias="PASSWORD_SPRAY_WINDOW_SECONDS")
    privilege_change_lookback_seconds: int = Field(default=900, alias="PRIVILEGE_CHANGE_LOOKBACK_SECONDS")
    large_download_threshold_bytes: int = Field(default=1_000_000, alias="LARGE_DOWNLOAD_THRESHOLD_BYTES")
    login_after_failures_threshold: int = Field(default=3, alias="LOGIN_AFTER_FAILURES_THRESHOLD")
    login_after_failures_window_seconds: int = Field(default=900, alias="LOGIN_AFTER_FAILURES_WINDOW_SECONDS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
