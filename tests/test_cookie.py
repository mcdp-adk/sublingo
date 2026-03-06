from __future__ import annotations

import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from sublingo.core.cookie import (
    save_cookie_text,
    validate_cookie_file,
    validate_cookie_with_ytdlp,
)


class TestValidateCookieFile:
    """Tests for validate_cookie_file function."""

    @pytest.fixture
    def temp_dir(self) -> Iterator[Path]:
        """Provide a temporary directory."""
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    def test_file_not_found(self, temp_dir: Path) -> None:
        """Test validation fails when file doesn't exist."""
        nonexistent = temp_dir / "nonexistent.txt"
        success, message = validate_cookie_file(nonexistent)
        assert success is False
        assert "not found" in message.lower()

    def test_empty_file(self, temp_dir: Path) -> None:
        """Test validation fails for empty file."""
        cookie_file = temp_dir / "cookies.txt"
        cookie_file.write_text("")
        success, message = validate_cookie_file(cookie_file)
        assert success is False
        assert "empty" in message.lower()

    def test_whitespace_only_file(self, temp_dir: Path) -> None:
        """Test validation fails for whitespace-only file."""
        cookie_file = temp_dir / "cookies.txt"
        cookie_file.write_text("   \n\t  ")
        success, message = validate_cookie_file(cookie_file)
        assert success is False
        assert "empty" in message.lower()

    def test_valid_netscape_format(self, temp_dir: Path) -> None:
        """Test validation passes for valid Netscape format."""
        cookie_file = temp_dir / "cookies.txt"
        # Netscape format: domain	flag	path	secure	expiration	name	value
        content = """# Netscape HTTP Cookie File
# This is a comment
.example.com	TRUE	/	FALSE	1893456000	cookie_name	cookie_value
.youtube.com	TRUE	/	TRUE	1893456000	SID	value123
"""
        cookie_file.write_text(content)
        success, message = validate_cookie_file(cookie_file)
        assert success is True
        assert "netscape" in message.lower()

    def test_valid_netscape_single_line(self, temp_dir: Path) -> None:
        """Test validation passes for Netscape format with single valid line."""
        cookie_file = temp_dir / "cookies.txt"
        # Single valid cookie line with 7+ tab-separated fields
        content = ".example.com\tTRUE\t/\tFALSE\t1893456000\tcookie_name\tcookie_value"
        cookie_file.write_text(content)
        success, message = validate_cookie_file(cookie_file)
        assert success is True
        assert "netscape" in message.lower()

    def test_invalid_netscape_too_few_fields(self, temp_dir: Path) -> None:
        """Test validation fails for Netscape format with too few fields."""
        cookie_file = temp_dir / "cookies.txt"
        # Only 3 fields instead of 7
        content = ".example.com\tTRUE\t/"
        cookie_file.write_text(content)
        success, message = validate_cookie_file(cookie_file)
        assert success is False
        assert "expected netscape" in message.lower()

    def test_invalid_format(self, temp_dir: Path) -> None:
        """Test validation fails for completely invalid format."""
        cookie_file = temp_dir / "cookies.txt"
        content = "This is not a valid cookie file format at all"
        cookie_file.write_text(content)
        success, message = validate_cookie_file(cookie_file)
        assert success is False
        assert "expected netscape" in message.lower()

    def test_json_cookie_content_is_rejected(self, temp_dir: Path) -> None:
        cookie_file = temp_dir / "cookies.txt"
        cookie_file.write_text('[{"name":"sid","value":"v"}]')
        success, message = validate_cookie_file(cookie_file)
        assert success is False
        assert "expected netscape" in message.lower()

    def test_binary_file_with_replacement(self, temp_dir: Path) -> None:
        """Test validation handles binary files with error replacement."""
        cookie_file = temp_dir / "cookies.txt"
        # Write some binary content
        cookie_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe")
        success, message = validate_cookie_file(cookie_file)
        assert success is False


class TestSaveCookieText:
    """Tests for save_cookie_text function."""

    @pytest.fixture
    def temp_dir(self) -> Iterator[Path]:
        """Provide a temporary directory."""
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    def test_save_valid_netscape_cookie_text(self, temp_dir: Path) -> None:
        dest = temp_dir / "internal" / "cookies.txt"
        content = (
            "# Netscape HTTP Cookie File\n"
            ".youtube.com\tTRUE\t/\tTRUE\t2147483647\tSID\tvalue"
        )
        success, message = save_cookie_text(content, dest)
        assert success is True
        assert "saved" in message.lower()
        assert dest.exists() is True
        assert "SID" in dest.read_text(encoding="utf-8")

    def test_save_rejects_empty_cookie_text(self, temp_dir: Path) -> None:
        success, message = save_cookie_text("   \n\t", temp_dir / "cookies.txt")
        assert success is False
        assert "empty" in message.lower()

    def test_save_rejects_non_netscape_cookie_text(self, temp_dir: Path) -> None:
        success, message = save_cookie_text('{"name":"sid"}', temp_dir / "cookies.txt")
        assert success is False
        assert "expected netscape" in message.lower()


class TestValidateCookieWithYtdlp:
    @pytest.fixture
    def temp_dir(self) -> Iterator[Path]:
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    def test_rejects_invalid_format_before_yt_dlp(
        self,
        temp_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        cookie_file = temp_dir / "cookies.txt"
        cookie_file.write_text("invalid", encoding="utf-8")

        class ProbeShouldNotRun:
            def __init__(self, *_args: Any, **_kwargs: Any) -> None:
                raise AssertionError("YoutubeDL should not be constructed")

        monkeypatch.setattr("sublingo.core.cookie.yt_dlp.YoutubeDL", ProbeShouldNotRun)

        success, message = validate_cookie_with_ytdlp(cookie_file, proxy=None)
        assert success is False
        assert "expected netscape" in message.lower()

    def test_reports_error_when_yt_dlp_fails(
        self,
        temp_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        cookie_file = temp_dir / "cookies.txt"
        cookie_file.write_text(
            ".youtube.com\tTRUE\t/\tTRUE\t2147483647\tSID\tvalue\n",
            encoding="utf-8",
        )

        class ProbeRaises:
            def __init__(self, *_args: Any, **_kwargs: Any) -> None:
                pass

            def __enter__(self) -> "ProbeRaises":
                return self

            def __exit__(self, *_args: Any) -> None:
                return None

            def extract_info(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
                raise RuntimeError("forbidden")

        monkeypatch.setattr("sublingo.core.cookie.yt_dlp.YoutubeDL", ProbeRaises)

        success, message = validate_cookie_with_ytdlp(cookie_file, proxy=None)
        assert success is False
        assert message.startswith("yt-dlp validation failed: ")

    def test_succeeds_when_yt_dlp_returns_video_info(
        self,
        temp_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        cookie_file = temp_dir / "cookies.txt"
        cookie_file.write_text(
            ".youtube.com\tTRUE\t/\tTRUE\t2147483647\tSID\tvalue\n",
            encoding="utf-8",
        )

        class ProbeReturnsInfo:
            def __init__(self, *_args: Any, **_kwargs: Any) -> None:
                pass

            def __enter__(self) -> "ProbeReturnsInfo":
                return self

            def __exit__(self, *_args: Any) -> None:
                return None

            def extract_info(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
                return {"id": "dQw4w9WgXcQ"}

        monkeypatch.setattr("sublingo.core.cookie.yt_dlp.YoutubeDL", ProbeReturnsInfo)

        success, message = validate_cookie_with_ytdlp(cookie_file, proxy=None)
        assert success is True
        assert "validated with yt-dlp" in message.lower()
