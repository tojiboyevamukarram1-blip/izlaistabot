from urllib.parse import urlparse
from bot.extractors.models import Platform


def detect_platform(url: str) -> Platform:
    """Detects the platform for a given URL."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]

        if host in {"youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"}:
            return Platform.YOUTUBE

        if host in {"instagram.com", "instagr.am"}:
            return Platform.INSTAGRAM

        if host in {"pinterest.com", "pin.it"} or host.endswith(".pinterest.com"):
            return Platform.PINTEREST

        return Platform.UNKNOWN
    except Exception:
        return Platform.UNKNOWN
