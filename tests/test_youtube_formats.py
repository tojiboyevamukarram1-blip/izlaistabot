import pytest
from unittest.mock import patch
from bot.extractors.youtube import YouTubeExtractor


@pytest.mark.asyncio
async def test_youtube_genuine_resolutions_selection():
    """Verify bot strictly selects ONLY genuinely available resolutions."""
    extractor = YouTubeExtractor()

    # Mock raw info with only 1080p and 360p video streams, and an audio stream
    mock_info = {
        "title": "Test Video",
        "uploader": "Test Channel",
        "duration": 120,
        "thumbnail": "https://example.com/thumb.jpg",
        "formats": [
            {
                "format_id": "140",
                "ext": "m4a",
                "vcodec": "none",
                "acodec": "mp4a.40.2",
                "abr": 128,
                "filesize": 2 * 1024 * 1024,  # 2 MB
            },
            {
                "format_id": "18",
                "ext": "mp4",
                "height": 360,
                "vcodec": "avc1.42001E",
                "acodec": "mp4a.40.2",
                "filesize": 5 * 1024 * 1024,  # 5 MB
            },
            {
                "format_id": "137",
                "ext": "mp4",
                "height": 1080,
                "vcodec": "avc1.640028",
                "acodec": "none",  # DASH video-only
                "filesize": 15 * 1024 * 1024,  # 15 MB
            },
        ],
    }

    with patch.object(extractor, "_sync_extract_info", return_value=mock_info):
        meta = await extractor.extract_metadata("https://www.youtube.com/watch?v=mock123")

    assert meta is not None
    assert meta.title == "Test Video"
    assert meta.author == "Test Channel"
    assert meta.duration == 120
    assert meta.duration_formatted == "02:00"

    # Check available resolutions
    resolutions = [f.resolution for f in meta.formats if not f.is_audio]
    # Only 1080p and 360p should exist! 2160p, 1440p, 720p, 480p, etc. must NOT be present!
    assert "1080p" in resolutions
    assert "360p" in resolutions
    assert "2160p" not in resolutions
    assert "1440p" not in resolutions
    assert "720p" not in resolutions
    assert "480p" not in resolutions

    # Check audio formats
    audio_formats = [f for f in meta.formats if f.is_audio]
    assert any("MP3" in f.resolution for f in audio_formats)
    assert any("audio" in f.resolution.lower() for f in audio_formats)

    # Check DASH size calculation: 1080p size should include audio size (15MB + 2MB = 17MB)
    f1080 = next(f for f in meta.formats if f.resolution == "1080p")
    assert f1080.requires_merge is True
    assert f1080.filesize == 17 * 1024 * 1024
    assert f1080.formatted_size == "~17.0 MB"
