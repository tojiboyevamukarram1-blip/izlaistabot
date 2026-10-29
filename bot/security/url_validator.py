import ipaddress
import re
import socket
from typing import Optional, Tuple
from urllib.parse import urlparse

# Regex to match URLs in user text
URL_REGEX = re.compile(
    r"(https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*))",
    re.IGNORECASE,
)

YOUTUBE_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "music.youtube.com",
}

INSTAGRAM_DOMAINS = {
    "instagram.com",
    "www.instagram.com",
    "instagr.am",
}

PINTEREST_DOMAINS = {
    "pinterest.com",
    "www.pinterest.com",
    "pin.it",
}


class SecurityValidationError(Exception):
    """Raised when URL fails security or SSRF checks."""
    pass


def extract_first_url(text: str) -> Optional[str]:
    """Finds and returns the first HTTP/HTTPS URL from a text message."""
    if not text:
        return None
    match = URL_REGEX.search(text)
    if match:
        return match.group(1).strip()
    return None


def is_ip_blocked(ip_str: str) -> bool:
    """Checks if IP is private, loopback, link-local, multicast, or reserved."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return False


def validate_url_security(url: str, resolve_dns: bool = True) -> Tuple[bool, str]:
    """
    Validates that a URL is safe against SSRF attacks and uses standard HTTP/S.
    Returns (is_valid, error_reason).
    """
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"URL parse error: {e}"

    if parsed.scheme.lower() not in ("http", "https"):
        return False, "Faqat HTTP va HTTPS protokollari qo'llab-quvvatlanadi."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL manzilda server nomi (hostname) topilmadi."

    hostname_lower = hostname.lower()

    # Block obvious local names
    if hostname_lower in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "local"):
        return False, "Lokal manzillarga kirish taqiqlangan."

    # Direct IP check (if hostname is an IP literal)
    try:
        ipaddress.ip_address(hostname_lower)
        if is_ip_blocked(hostname_lower):
            return False, "Xavfsizlik: Ichki IP manzillarga kirish taqiqlangan."
    except ValueError:
        pass  # It's a domain name, not an IP literal

    # SSRF DNS Resolution check
    if resolve_dns:
        try:
            addr_info = socket.getaddrinfo(hostname_lower, None)
            for item in addr_info:
                ip_addr = item[4][0]
                if is_ip_blocked(ip_addr):
                    return False, "Xavfsizlik: Ushbu havola ichki tarmoqqa yo'naltirilgan (SSRF)."
        except socket.gaierror:
            return False, "Server nomini aniqlab (DNS) bo'lmadi."
        except Exception as e:
            return False, f"DNS tekshiruvida xatolik: {e}"

    return True, ""


def is_supported_platform_url(url: str) -> bool:
    """Checks if hostname matches Instagram, YouTube, or Pinterest."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host_clean = host[4:]
        else:
            host_clean = host

        if host in YOUTUBE_DOMAINS or host_clean in YOUTUBE_DOMAINS:
            return True
        if host in INSTAGRAM_DOMAINS or host_clean in INSTAGRAM_DOMAINS:
            return True
        if host in PINTEREST_DOMAINS or host_clean in PINTEREST_DOMAINS or host.endswith(".pinterest.com"):
            return True

        return False
    except Exception:
        return False
