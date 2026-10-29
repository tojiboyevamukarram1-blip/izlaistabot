import pytest
from bot.security.url_validator import (
    extract_first_url,
    is_ip_blocked,
    is_supported_platform_url,
    validate_url_security,
)


def test_extract_first_url():
    assert extract_first_url("Salom https://youtube.com/watch?v=123 rahmat") == "https://youtube.com/watch?v=123"
    assert extract_first_url("Qarang: http://instagram.com/reel/xyz/") == "http://instagram.com/reel/xyz/"
    assert extract_first_url("Havola yo'q bu yerda") is None
    assert extract_first_url("") is None


def test_is_ip_blocked():
    # Loopback
    assert is_ip_blocked("127.0.0.1") is True
    assert is_ip_blocked("127.0.0.2") is True
    assert is_ip_blocked("::1") is True

    # Private IP ranges
    assert is_ip_blocked("10.0.0.1") is True
    assert is_ip_blocked("172.16.0.5") is True
    assert is_ip_blocked("192.168.1.100") is True

    # Link-local / Cloud metadata service
    assert is_ip_blocked("169.254.169.254") is True

    # Public safe IPs
    assert is_ip_blocked("8.8.8.8") is False
    assert is_ip_blocked("1.1.1.1") is False


def test_validate_url_security_schemes():
    # Only HTTP / HTTPS allowed
    valid, _ = validate_url_security("ftp://example.com/file", resolve_dns=False)
    assert valid is False

    valid, _ = validate_url_security("file:///etc/passwd", resolve_dns=False)
    assert valid is False

    valid, _ = validate_url_security("javascript:alert(1)", resolve_dns=False)
    assert valid is False


def test_validate_url_security_ssrf():
    # Localhost
    valid, msg = validate_url_security("http://localhost:8080/admin", resolve_dns=False)
    assert valid is False

    valid, msg = validate_url_security("http://127.0.0.1/status", resolve_dns=False)
    assert valid is False

    valid, msg = validate_url_security("http://169.254.169.254/latest/meta-data/", resolve_dns=False)
    assert valid is False

    valid, msg = validate_url_security("http://192.168.1.1/router", resolve_dns=False)
    assert valid is False


def test_is_supported_platform_url():
    # YouTube
    assert is_supported_platform_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert is_supported_platform_url("https://youtu.be/dQw4w9WgXcQ") is True
    assert is_supported_platform_url("https://youtube.com/shorts/abcdef12345") is True
    assert is_supported_platform_url("https://m.youtube.com/watch?v=xyz") is True

    # Instagram
    assert is_supported_platform_url("https://www.instagram.com/reel/Cx12345678/") is True
    assert is_supported_platform_url("https://instagram.com/p/ABC123xyz/") is True
    assert is_supported_platform_url("https://instagr.am/p/ABC123xyz/") is True

    # Pinterest
    assert is_supported_platform_url("https://www.pinterest.com/pin/123456789/") is True
    assert is_supported_platform_url("https://pin.it/abcXYZ1") is True

    # Unsupported platforms
    assert is_supported_platform_url("https://tiktok.com/@user/video/123") is False
    assert is_supported_platform_url("https://facebook.com/watch/?v=123") is False
    assert is_supported_platform_url("https://twitter.com/user/status/123") is False
    assert is_supported_platform_url("https://malicious-site.com/exploit") is False
