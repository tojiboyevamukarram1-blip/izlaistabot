from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Platform(str, Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    PINTEREST = "pinterest"
    UNKNOWN = "unknown"


class MediaType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    PHOTO = "photo"
    CAROUSEL = "carousel"
    DOCUMENT = "document"


class MediaFormat(BaseModel):
    """Represents a genuinely available quality or audio format option."""

    format_id: str
    resolution: str  # e.g., "1080p", "720p", "480p", "MP3"
    ext: str = "mp4"
    filesize: Optional[int] = None  # Exact bytes
    filesize_approx: Optional[int] = None  # Estimated bytes
    note: str = ""
    is_audio: bool = False
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    requires_merge: bool = False

    @property
    def effective_filesize(self) -> Optional[int]:
        return self.filesize if self.filesize else self.filesize_approx

    @property
    def formatted_size(self) -> str:
        size = self.effective_filesize
        if not size or size <= 0:
            return ""
        size_mb = size / (1024 * 1024)
        if size_mb < 1.0:
            return f"~{size / 1024:.0f} KB"
        return f"~{size_mb:.1f} MB"


class MediaItem(BaseModel):
    """Represents an individual media item (e.g. one image in an Instagram carousel)."""

    url: str
    type: MediaType = MediaType.PHOTO
    thumbnail: Optional[str] = None


class MediaMetadata(BaseModel):
    """Standardized metadata extracted from any supported platform."""

    platform: Platform
    url: str
    title: str = "Media"
    author: str = "Noma'lum muallif"
    duration: Optional[int] = None  # In seconds
    thumbnail: Optional[str] = None
    formats: List[MediaFormat] = Field(default_factory=list)
    items: List[MediaItem] = Field(default_factory=list)  # For carousel or multi-items
    is_carousel: bool = False
    media_type: MediaType = MediaType.VIDEO
    cache_key: str = ""

    @property
    def duration_formatted(self) -> str:
        if not self.duration:
            return "Noma'lum"
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes:02d}:{seconds:02d}"
