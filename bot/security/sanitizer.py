import os
import re
import shutil
from pathlib import Path
from typing import Optional


ILLEGAL_CHARS_PATTERN = re.compile(r'[\\/*?:"<>|\x00-\x1f]')


def sanitize_filename(filename: str, max_length: int = 100, default: str = "media") -> str:
    """
    Sanitizes a string to be safely used as a filename across Windows and Linux.
    Removes invalid characters, path traversal, and trims length.
    """
    if not filename:
        return default

    # Remove illegal filename characters
    cleaned = ILLEGAL_CHARS_PATTERN.sub("_", filename).strip()

    # Prevent path traversal components
    cleaned = cleaned.replace("..", "_").replace("/", "_").replace("\\", "_")

    # Strip leading/trailing dots, spaces, and underscores
    cleaned = cleaned.strip(". _")

    if not cleaned or not cleaned.replace("_", ""):
        return default

    # Limit length
    if len(cleaned) > max_length:
        base, sep, ext = cleaned.rpartition(".")
        if sep and len(ext) <= 10:
            cleaned = base[: max_length - len(ext) - 1] + "." + ext
        else:
            cleaned = cleaned[:max_length]

    return cleaned


def create_safe_task_dir(base_temp_dir: Path, user_id: int, task_id: str) -> Path:
    """Creates an isolated directory for a user task."""
    task_dir = base_temp_dir / f"user_{user_id}" / sanitize_filename(task_id, max_length=32)
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir


def cleanup_directory(path: Optional[Path]) -> None:
    """Safely removes a temporary directory and all contents."""
    if path is None:
        return
    try:
        if path.exists() and path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists() and path.is_file():
            path.unlink(missing_ok=True)
    except Exception:
        pass
