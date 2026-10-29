import pytest
from bot.extractors.models import MediaFormat, MediaMetadata, MediaType, Platform
from bot.handlers.keyboards import (
    get_instagram_keyboard,
    get_pinterest_keyboard,
    get_youtube_keyboard,
)


def test_youtube_keyboard_callback_data_length():
    """Ensure all callback_data strings are strictly within Telegram's 64-byte limit."""
    formats = [
        MediaFormat(format_id="137+140", resolution="1080p", filesize=25000000),
        MediaFormat(format_id="22", resolution="720p", filesize=12000000),
        MediaFormat(format_id="18", resolution="360p", filesize=5000000),
        MediaFormat(format_id="bestaudio", resolution="MP3", is_audio=True, filesize=3000000),
        MediaFormat(format_id="140", resolution="Asl audio", is_audio=True, filesize=3000000),
    ]
    meta = MediaMetadata(
        platform=Platform.YOUTUBE,
        url="https://youtube.com/watch?v=123",
        title="Test Video with Long Title",
        cache_key="yt:abcd1234efgh",
        formats=formats,
    )

    kb = get_youtube_keyboard(meta)
    for row in kb.inline_keyboard:
        for btn in row:
            # Telegram callback_data max length is 64 bytes
            cb_bytes = btn.callback_data.encode("utf-8")
            assert len(cb_bytes) <= 64, f"Callback data too long: {btn.callback_data} ({len(cb_bytes)} bytes)"


def test_pinterest_keyboard():
    meta = MediaMetadata(
        platform=Platform.PINTEREST,
        url="https://pin.it/123",
        title="Test Pin",
        cache_key="pin:abcd1234efgh",
    )
    kb = get_pinterest_keyboard(meta, is_video=False)
    for row in kb.inline_keyboard:
        for btn in row:
            assert len(btn.callback_data.encode("utf-8")) <= 64

    kb_vid = get_pinterest_keyboard(meta, is_video=True)
    for row in kb_vid.inline_keyboard:
        for btn in row:
            assert len(btn.callback_data.encode("utf-8")) <= 64


def test_instagram_keyboard():
    meta = MediaMetadata(
        platform=Platform.INSTAGRAM,
        url="https://instagram.com/reel/123",
        title="Test Reel",
        cache_key="ig:abcd1234efgh",
        is_carousel=False,
    )
    kb = get_instagram_keyboard(meta)
    for row in kb.inline_keyboard:
        for btn in row:
            assert len(btn.callback_data.encode("utf-8")) <= 64


def test_callback_data_parsing():
    cb_data = "dl:ig:abcd1234efgh:ig_vid"
    parts = cb_data.split(":")
    assert len(parts) >= 3
    action = parts[-1]
    cache_key = ":".join(parts[1:-1])
    assert action == "ig_vid"
    assert cache_key == "ig:abcd1234efgh"
