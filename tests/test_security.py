import os
from pathlib import Path
from bot.security.sanitizer import (
    cleanup_directory,
    create_safe_task_dir,
    sanitize_filename,
)


def test_sanitize_filename_path_traversal():
    assert ".." not in sanitize_filename("../../../etc/passwd")
    assert "/" not in sanitize_filename("../../../etc/passwd")
    assert "\\" not in sanitize_filename("..\\..\\windows\\system32")


def test_sanitize_filename_illegal_chars():
    dirty = 'Video: <Awesome> "Title" / with | bad * chars?'
    cleaned = sanitize_filename(dirty)
    for char in '<>:"/\\|?*':
        assert char not in cleaned


def test_sanitize_filename_length_and_default():
    assert sanitize_filename("") == "media"
    assert sanitize_filename("   ") == "media"
    assert sanitize_filename("...") == "media"

    long_name = "a" * 200 + ".mp4"
    sanitized = sanitize_filename(long_name, max_length=50)
    assert len(sanitized) <= 50
    assert sanitized.endswith(".mp4")


def test_create_and_cleanup_task_dir(tmp_path: Path):
    user_id = 999888
    task_id = "test_task_abc"

    task_dir = create_safe_task_dir(tmp_path, user_id, task_id)
    assert task_dir.exists()
    assert task_dir.is_dir()
    assert f"user_{user_id}" in str(task_dir)

    # Create dummy file inside
    dummy_file = task_dir / "test.txt"
    dummy_file.write_text("hello")
    assert dummy_file.exists()

    # Clean up
    cleanup_directory(task_dir)
    assert not task_dir.exists()
