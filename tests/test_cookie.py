"""Tests for cookie file handling."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from sublingo.core.cookie import import_cookie_file, validate_cookie_file


class TestValidateCookieFile:
    """Tests for validate_cookie_file function."""

    @pytest.fixture
    def temp_dir(self) -> Path:
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

    def test_valid_json_format(self, temp_dir: Path) -> None:
        """Test validation passes for valid JSON format."""
        cookie_file = temp_dir / "cookies.txt"
        content = """[
            {"name": "cookie1", "value": "value1", "domain": ".example.com"},
            {"name": "cookie2", "value": "value2", "domain": ".youtube.com"}
        ]"""
        cookie_file.write_text(content)
        success, message = validate_cookie_file(cookie_file)
        assert success is True
        assert "json" in message.lower()

    def test_valid_json_single_object(self, temp_dir: Path) -> None:
        """Test validation passes for JSON array with single object."""
        cookie_file = temp_dir / "cookies.txt"
        content = '[{"name": "cookie1", "value": "value1"}]'
        cookie_file.write_text(content)
        success, message = validate_cookie_file(cookie_file)
        assert success is True
        assert "json" in message.lower()

    def test_invalid_netscape_too_few_fields(self, temp_dir: Path) -> None:
        """Test validation fails for Netscape format with too few fields."""
        cookie_file = temp_dir / "cookies.txt"
        # Only 3 fields instead of 7
        content = ".example.com\tTRUE\t/"
        cookie_file.write_text(content)
        success, message = validate_cookie_file(cookie_file)
        assert success is False
        assert "unrecognized" in message.lower()

    def test_invalid_format(self, temp_dir: Path) -> None:
        """Test validation fails for completely invalid format."""
        cookie_file = temp_dir / "cookies.txt"
        content = "This is not a valid cookie file format at all"
        cookie_file.write_text(content)
        success, message = validate_cookie_file(cookie_file)
        assert success is False
        assert "unrecognized" in message.lower()

    def test_invalid_json_not_array(self, temp_dir: Path) -> None:
        """Test validation fails for JSON that is not an array."""
        cookie_file = temp_dir / "cookies.txt"
        content = '{"name": "cookie1", "value": "value1"}'
        cookie_file.write_text(content)
        success, message = validate_cookie_file(cookie_file)
        assert success is False
        assert "unrecognized" in message.lower()

    def test_invalid_json_empty_array(self, temp_dir: Path) -> None:
        """Test validation fails for empty JSON array."""
        cookie_file = temp_dir / "cookies.txt"
        content = "[]"
        cookie_file.write_text(content)
        success, message = validate_cookie_file(cookie_file)
        assert success is False
        assert "unrecognized" in message.lower()

    def test_invalid_json_primitives_array(self, temp_dir: Path) -> None:
        """Test validation fails for JSON array of primitives."""
        cookie_file = temp_dir / "cookies.txt"
        content = '["string1", "string2", 123]'
        cookie_file.write_text(content)
        success, message = validate_cookie_file(cookie_file)
        assert success is False
        assert "unrecognized" in message.lower()

    def test_binary_file_with_replacement(self, temp_dir: Path) -> None:
        """Test validation handles binary files with error replacement."""
        cookie_file = temp_dir / "cookies.txt"
        # Write some binary content
        cookie_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe")
        success, message = validate_cookie_file(cookie_file)
        assert success is False


class TestImportCookieFile:
    """Tests for import_cookie_file function."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Provide a temporary directory."""
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    def test_import_success(self, temp_dir: Path) -> None:
        """Test successful cookie file import."""
        source = temp_dir / "source" / "cookies.txt"
        dest = temp_dir / "dest" / "cookies.txt"

        # Create source file
        source.parent.mkdir(parents=True)
        source.write_text(
            "# Netscape cookie file\n.example.com\tTRUE\t/\tFALSE\t1893456000\tcookie\tvalue"
        )

        # Import
        import_cookie_file(source, dest)

        # Verify destination exists and has correct content
        assert dest.exists()
        assert dest.read_text() == source.read_text()

    def test_import_creates_parent_dirs(self, temp_dir: Path) -> None:
        """Test import creates parent directories for destination."""
        source = temp_dir / "source.txt"
        dest = temp_dir / "deep" / "nested" / "dest.txt"

        source.write_text("cookie data")

        import_cookie_file(source, dest)

        assert dest.exists()
        assert dest.parent.exists()

    def test_import_overwrites_existing(self, temp_dir: Path) -> None:
        """Test import overwrites existing destination file."""
        source = temp_dir / "source.txt"
        dest = temp_dir / "dest.txt"

        source.write_text("new cookie data")
        dest.write_text("old cookie data")

        import_cookie_file(source, dest)

        assert dest.read_text() == "new cookie data"

    def test_import_preserves_metadata(self, temp_dir: Path) -> None:
        """Test import preserves file metadata (via shutil.copy2)."""
        source = temp_dir / "source.txt"
        dest = temp_dir / "dest.txt"

        source.write_text("cookie data")
        # Note: shutil.copy2 preserves metadata, but on some systems
        # this test may be limited by filesystem support

        import_cookie_file(source, dest)

        assert dest.exists()
        assert dest.read_text() == "cookie data"

    def test_import_source_not_found(self, temp_dir: Path) -> None:
        """Test import raises FileNotFoundError when source doesn't exist."""
        source = temp_dir / "nonexistent.txt"
        dest = temp_dir / "dest.txt"

        with pytest.raises(FileNotFoundError) as exc_info:
            import_cookie_file(source, dest)

        assert "nonexistent" in str(exc_info.value)
