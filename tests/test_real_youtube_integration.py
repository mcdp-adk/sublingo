from __future__ import annotations

from pathlib import Path

import pytest

from sublingo.core.downloader import extract_info

YOUTUBE_VIDEO_ID: str = "dQw4w9WgXcQ"
YOUTUBE_VIDEO_URL: str = f"https://www.youtube.com/watch?v={YOUTUBE_VIDEO_ID}"
NETSCAPE_COOKIE_HEADER: str = "# Netscape HTTP Cookie File\n"

pytestmark = pytest.mark.e2e


def test_extract_info_from_real_youtube_video(tmp_path: Path) -> None:
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text(NETSCAPE_COOKIE_HEADER, encoding="utf-8")

    info = extract_info(YOUTUBE_VIDEO_URL, cookie_file=cookie_file, proxy=None)

    assert info.video_id == YOUTUBE_VIDEO_ID
    assert info.title
    assert info.url
    assert info.duration > 0
