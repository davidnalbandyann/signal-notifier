import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import ClassVar


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    AUTH_USERNAME: str = ""
    AUTH_PASSWORD: str = ""
    JWT_SECRET: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 72

    CHECK_INTERVAL_SECONDS: int = 60
    NOTIFICATION_THRESHOLD: float = 8.0
    PLAYWRIGHT_WAIT_TIME: int = 5
    HEADLESS: bool = True
    BROWSER_VIEWPORT_WIDTH: int = 1920
    BROWSER_VIEWPORT_HEIGHT: int = 1080

    TELEGRAM_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    NVIDIA_API_KEY: str = ""
    NVIDIA_MODEL: str = "minimaxai/minimax-m3"
    AI_CALL_DELAY: float = 2.0

    BROWSER_USER_DATA_DIR: str = ""
    BROWSER_RETRY_COUNT: int = 2
    BROWSER_RETRY_DELAY: int = 3

    URLS_FILE: str = "urls.yaml"

    TRIGGER_TOKEN: str = ""

    REQUIRED_ENVVARS: ClassVar[list[str]] = [
        "TELEGRAM_TOKEN",
        "TELEGRAM_CHAT_ID",
        "NVIDIA_API_KEY",
    ]

    def validate_required(self) -> None:
        missing = [v for v in self.REQUIRED_ENVVARS if not getattr(self, v)]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Set them in .env or export them."
            )
