import shutil
from pathlib import Path
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    bot_token: str = Field(
        default="",
        description="Telegram bot token obtained from @BotFather",
    )
    owner_id: Optional[int] = Field(
        default=None,
        description="Numeric Telegram user ID of the owner. When set, only this user can use the bot.",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching and rate limiting",
    )
    max_file_size_mb: int = Field(
        default=50,
        description="Maximum file size in Megabytes for Telegram bot uploads",
    )
    max_duration_seconds: int = Field(
        default=14400,
        description="Maximum video duration allowed in seconds (e.g. 14400 = 4 hours)",
    )
    max_concurrent_downloads: int = Field(
        default=5,
        description="Maximum simultaneous yt-dlp download workers",
    )
    rate_limit_requests: int = Field(
        default=5,
        description="Number of requests allowed per user within rate_limit_window",
    )
    rate_limit_window: int = Field(
        default=30,
        description="Rate limit sliding window in seconds",
    )
    request_timeout: int = Field(
        default=60,
        description="Network extraction and API timeout in seconds",
    )
    ffmpeg_path: str = Field(
        default="ffmpeg",
        description="Path to ffmpeg binary",
    )
    temp_dir: Path = Field(
        default=Path("temp_media"),
        description="Path to temporary download directory",
    )
    cookies_file: Optional[Path] = Field(
        default=None,
        description="Optional path to Netscape cookies.txt file",
    )
    admin_ids: List[int] = Field(
        default_factory=list,
        description="List of Telegram user IDs with administrative access",
    )

    @field_validator("owner_id", mode="before")
    @classmethod
    def parse_owner_id(cls, v):
        if v is None or v == "" or (isinstance(v, str) and not v.strip()):
            return None
        return int(v)

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",") if x.strip().isdigit()]
        if isinstance(v, (list, tuple)):
            return [int(x) for x in v]
        return []

    @property
    def resolved_ffmpeg_path(self) -> str:
        """Finds absolute path to ffmpeg binary, or falls back to configured value."""
        found = shutil.which(self.ffmpeg_path)
        return found if found else self.ffmpeg_path

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
