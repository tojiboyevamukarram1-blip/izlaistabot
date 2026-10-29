from bot.extractors.detector import detect_platform
from bot.extractors.models import Platform


def test_detect_platform_youtube():
    assert detect_platform("https://www.youtube.com/watch?v=123") == Platform.YOUTUBE
    assert detect_platform("https://youtu.be/123") == Platform.YOUTUBE
    assert detect_platform("https://m.youtube.com/watch?v=123") == Platform.YOUTUBE
    assert detect_platform("https://youtube.com/shorts/xyz") == Platform.YOUTUBE


def test_detect_platform_instagram():
    assert detect_platform("https://www.instagram.com/reel/xyz123/") == Platform.INSTAGRAM
    assert detect_platform("https://instagram.com/p/abc_123/") == Platform.INSTAGRAM
    assert detect_platform("https://instagr.am/p/abc_123/") == Platform.INSTAGRAM


def test_detect_platform_pinterest():
    assert detect_platform("https://www.pinterest.com/pin/123456789/") == Platform.PINTEREST
    assert detect_platform("https://pin.it/abc1234") == Platform.PINTEREST
    assert detect_platform("https://uk.pinterest.com/pin/123456789/") == Platform.PINTEREST


def test_detect_platform_unknown():
    assert detect_platform("https://google.com") == Platform.UNKNOWN
    assert detect_platform("https://tiktok.com/@video/123") == Platform.UNKNOWN
    assert detect_platform("not a url") == Platform.UNKNOWN
