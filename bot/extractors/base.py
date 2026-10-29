from abc import ABC, abstractmethod
from typing import Optional
from bot.extractors.models import MediaMetadata


class BaseExtractor(ABC):
    """Abstract base class for platform-specific media extractors."""

    @abstractmethod
    async def extract_metadata(self, url: str) -> Optional[MediaMetadata]:
        """Extracts metadata and genuinely available formats for the media URL."""
        pass
