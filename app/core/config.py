from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Trendsee MVP"
    environment: str = "dev"
    debug: bool = True

    database_url: str = "sqlite+aiosqlite:///./trendsee.db"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    celery_task_always_eager: bool = False

    upload_dir: Path = Path("uploads")
    max_upload_mb: int = 25
    base_url: str = "http://localhost:8000"

    default_user_api_key: str = "dev-user-key"
    default_admin_api_key: str = "dev-admin-key"
    initial_token_balance: int = 1000
    admin_token: str = "admin-ui-token"

    model_provider: str = "mock"
    openrouter_api_key: str | None = None
    openrouter_model: str = "openai/gpt-4o-mini"

    mock_min_delay_sec: float = 1.0
    mock_max_delay_sec: float = 2.0
    sse_poll_interval_sec: float = 1.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):  # noqa: ANN001
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value

    @property
    def resolved_upload_dir(self) -> Path:
        return self.upload_dir if self.upload_dir.is_absolute() else Path.cwd() / self.upload_dir

    @property
    def effective_celery_broker(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def effective_celery_backend(self) -> str:
        return self.celery_result_backend or self.redis_url


settings = Settings()
settings.resolved_upload_dir.mkdir(parents=True, exist_ok=True)
