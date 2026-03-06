"""Cookie file validation and import for yt-dlp."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

import yt_dlp

logger = logging.getLogger(__name__)
COOKIE_VALIDATION_TEST_URL: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def validate_cookie_file(path: Path) -> tuple[bool, str]:
    """Validate a cookie file format.

    Checks for valid Netscape format (tab-separated fields).

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

    return False, "Invalid cookie format (expected Netscape)"


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


def save_cookie_text(content: str, dest: Path) -> tuple[bool, str]:
    normalized = content.strip()
    if not normalized:
        return False, "Cookie content is empty"
    if not _is_netscape_format(normalized):
        logger.debug("Invalid Netscape cookie content: %s", normalized[:120])
        return False, "Invalid cookie format (expected Netscape)"

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(f"{normalized}\n", encoding="utf-8")
    return True, "Cookie saved"


def validate_cookie_with_ytdlp(
    cookie_file: Path,
    *,
    proxy: str | None,
    test_url: str = COOKIE_VALIDATION_TEST_URL,
) -> tuple[bool, str]:
    format_ok, format_message = validate_cookie_file(cookie_file)
    if not format_ok:
        return False, format_message

    opts: dict[str, object] = {
        "cookiefile": str(cookie_file),
        "extract_flat": True,
        "simulate": True,
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 20,
    }
    if proxy is not None:
        opts["proxy"] = proxy

    try:
        with yt_dlp.YoutubeDL(cast(Any, opts)) as ydl:
            info = ydl.extract_info(test_url, download=False, process=False)
    except Exception as exc:
        return False, f"yt-dlp validation failed: {exc}"

    if not isinstance(info, dict):
        return False, "yt-dlp validation failed: invalid probe result"
    if not info.get("id"):
        return False, "yt-dlp validation failed: missing video id"
    return True, "Cookie validated with yt-dlp"
