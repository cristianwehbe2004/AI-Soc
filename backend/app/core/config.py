from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="ai-soc", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        alias="CORS_ORIGINS",
    )
    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field(..., alias="REDIS_URL")
    secret_key: str = Field(..., alias="SECRET_KEY")
    auth_jwt_issuer: str = Field(default="ai-soc", alias="AUTH_JWT_ISSUER")
    auth_jwt_audience: str = Field(default="ai-soc-api", alias="AUTH_JWT_AUDIENCE")
    auth_access_token_minutes: int = Field(default=15, ge=1, le=60, alias="AUTH_ACCESS_TOKEN_MINUTES")
    auth_refresh_token_days: int = Field(default=7, ge=1, le=30, alias="AUTH_REFRESH_TOKEN_DAYS")
    auth_refresh_cookie_name: str = Field(default="ai_soc_refresh", alias="AUTH_REFRESH_COOKIE_NAME")
    auth_cookie_secure: bool = Field(default=False, alias="AUTH_COOKIE_SECURE")
    auth_login_window_seconds: int = Field(default=900, ge=60, alias="AUTH_LOGIN_WINDOW_SECONDS")
    auth_login_account_limit: int = Field(default=5, ge=1, alias="AUTH_LOGIN_ACCOUNT_LIMIT")
    auth_login_ip_limit: int = Field(default=20, ge=1, alias="AUTH_LOGIN_IP_LIMIT")
    llm_enabled: bool = Field(default=False, alias="LLM_ENABLED")
    llm_provider: str = Field(default="disabled", alias="LLM_PROVIDER")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_model: str = Field(default="gpt-5-mini", alias="LLM_MODEL")
    llm_timeout_seconds: float = Field(default=60.0, gt=0, alias="LLM_TIMEOUT_SECONDS")
    llm_max_retries: int = Field(default=2, ge=0, le=10, alias="LLM_MAX_RETRIES")
    llm_max_output_tokens: int = Field(default=2000, ge=256, alias="LLM_MAX_OUTPUT_TOKENS")
    llm_prompt_version: str = Field(default="v1", alias="LLM_PROMPT_VERSION")
    llm_context_max_chars: int = Field(default=30_000, ge=5000, alias="LLM_CONTEXT_MAX_CHARS")
    investigation_queue_key: str = Field(
        default="ai_soc:investigations",
        alias="INVESTIGATION_QUEUE_KEY",
    )
    investigation_worker_block_seconds: int = Field(
        default=5,
        ge=1,
        le=60,
        alias="INVESTIGATION_WORKER_BLOCK_SECONDS",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    brute_force_threshold: int = Field(default=10, alias="BRUTE_FORCE_THRESHOLD")
    brute_force_window_seconds: int = Field(default=60, alias="BRUTE_FORCE_WINDOW_SECONDS")
    password_spray_unique_users: int = Field(default=5, alias="PASSWORD_SPRAY_UNIQUE_USERS")
    password_spray_window_seconds: int = Field(default=300, alias="PASSWORD_SPRAY_WINDOW_SECONDS")
    privilege_change_lookback_seconds: int = Field(default=900, alias="PRIVILEGE_CHANGE_LOOKBACK_SECONDS")
    large_download_threshold_bytes: int = Field(default=1_000_000, alias="LARGE_DOWNLOAD_THRESHOLD_BYTES")
    login_after_failures_threshold: int = Field(default=3, alias="LOGIN_AFTER_FAILURES_THRESHOLD")
    login_after_failures_window_seconds: int = Field(default=900, alias="LOGIN_AFTER_FAILURES_WINDOW_SECONDS")
    credential_compromise_lookback_seconds: int = Field(
        default=1800,
        alias="CREDENTIAL_COMPROMISE_LOOKBACK_SECONDS",
    )
    incident_merge_window_seconds: int = Field(default=3600, alias="INCIDENT_MERGE_WINDOW_SECONDS")
    risk_score_high_severity_weight: int = Field(default=20, alias="RISK_SCORE_HIGH_SEVERITY_WEIGHT")
    risk_score_medium_severity_weight: int = Field(default=10, alias="RISK_SCORE_MEDIUM_SEVERITY_WEIGHT")
    risk_score_low_severity_weight: int = Field(default=5, alias="RISK_SCORE_LOW_SEVERITY_WEIGHT")
    risk_score_confidence_multiplier: int = Field(default=20, alias="RISK_SCORE_CONFIDENCE_MULTIPLIER")
    risk_score_combo_bonus: int = Field(default=15, alias="RISK_SCORE_COMBO_BONUS")
    risk_score_supporting_bonus: int = Field(default=10, alias="RISK_SCORE_SUPPORTING_BONUS")
    ml_enabled: bool = Field(default=True, alias="ML_ENABLED")
    ml_model_name: str = Field(default="isolation_forest_v1", alias="ML_MODEL_NAME")
    ml_artifact_dir: str = Field(default="/app/artifacts/models", alias="ML_ARTIFACT_DIR")
    ml_aggregation_window_seconds: int = Field(default=300, alias="ML_AGGREGATION_WINDOW_SECONDS")
    ml_training_lookback_days: int = Field(default=30, alias="ML_TRAINING_LOOKBACK_DAYS")
    ml_min_training_rows: int = Field(default=200, alias="ML_MIN_TRAINING_ROWS")
    ml_isolation_forest_contamination: float = Field(default=0.05, alias="ML_ISOLATION_FOREST_CONTAMINATION")
    ml_isolation_forest_random_state: int = Field(default=42, alias="ML_ISOLATION_FOREST_RANDOM_STATE")
    ml_anomaly_alert_threshold: float = Field(default=-0.15, alias="ML_ANOMALY_ALERT_THRESHOLD")
    ml_feature_version: str = Field(default="v1", alias="ML_FEATURE_VERSION")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_secret_key(self) -> "Settings":
        if self.app_env.lower() not in {"development", "test"} and (
            self.secret_key == "change-me" or len(self.secret_key) < 32
        ):
            raise ValueError("SECRET_KEY must be at least 32 characters outside development/test")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
