"""Cookie file validation and import for yt-dlp."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


def validate_cookie_file(path: Path) -> tuple[bool, str]:
    """Validate a cookie file format.

    Checks for valid Netscape format (tab-separated) or JSON format.

    Args:
        path: Path to the cookie file.

    Returns:
        Tuple of (success, message). Success is True if valid.
    """
    if not path.exists():
        return False, "Cookie file not found"

    content = path.read_text(encoding="utf-8", errors="replace").strip()
    if not content:
        return False, "Cookie file is empty"

    # Check Netscape format (lines with tab-separated fields)
    if _is_netscape_format(content):
        return True, "Valid Netscape cookie format"

    # Check JSON format
    if _is_json_format(content):
        return True, "Valid JSON cookie format"

    return False, "Unrecognized cookie format (expected Netscape or JSON)"


def _is_netscape_format(content: str) -> bool:
    """Check if content follows Netscape cookie format.

    Netscape format has tab-separated fields with at least 7 columns per line.
    """
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            return True
    return False


def _is_json_format(content: str) -> bool:
    """Check if content is valid JSON cookie format.

    JSON format should be a list of cookie objects.
    """
    try:
        data = json.loads(content)
        if isinstance(data, list) and data:
            return isinstance(data[0], dict)
    except (json.JSONDecodeError, IndexError):
        pass
    return False


def import_cookie_file(source: Path, dest: Path) -> None:
    """Copy cookie file to project location.

    Args:
        source: Source cookie file path.
        dest: Destination path (typically project's cookies.txt).

    Raises:
        FileNotFoundError: If source file does not exist.
        OSError: If copy operation fails.
    """
    if not source.exists():
        raise FileNotFoundError(f"Source cookie file not found: {source}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
