from __future__ import annotations

from pathlib import Path

import pytest

from sublingo.core.models import TranscriptResult
from sublingo.core.transcript import generate_transcript

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_vtt_input_produces_correct_transcript(tmp_path: Path):
    subtitle_path = FIXTURES_DIR / "sample.en.vtt"

    result = generate_transcript(subtitle_path, output_dir=tmp_path)

    assert result.success is True
    assert result.transcript_path is not None
    assert result.transcript_path.exists()
    content = result.transcript_path.read_text(encoding="utf-8")
    assert "Hello world" in content
    assert "This is a test." in content


def test_srt_input_produces_correct_transcript(tmp_path: Path):
    subtitle_path = FIXTURES_DIR / "sample.en.srt"

    result = generate_transcript(subtitle_path, output_dir=tmp_path)

    assert result.success is True
    assert result.transcript_path is not None
    assert result.transcript_path.exists()
    content = result.transcript_path.read_text(encoding="utf-8")
    assert "Hello world" in content
    assert "This is a test." in content


def test_duplicate_lines_are_deduplicated(tmp_path: Path):
    # Create a subtitle file with duplicate consecutive lines
    subtitle_content = """WEBVTT

00:00:00.000 --> 00:00:01.000
Hello world

00:00:01.100 --> 00:00:02.000
Hello world

00:00:02.100 --> 00:00:03.000
This is unique.

00:00:03.100 --> 00:00:04.000
This is unique.

00:00:04.100 --> 00:00:05.000
Final line.
"""
    subtitle_path = tmp_path / "duplicates.vtt"
    subtitle_path.write_text(subtitle_content, encoding="utf-8")

    result = generate_transcript(subtitle_path)

    assert result.success is True
    assert result.transcript_path is not None
    content = result.transcript_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    assert lines == ["Hello world", "This is unique.", "Final line."]


def test_output_file_naming_follows_convention(tmp_path: Path):
    subtitle_path = FIXTURES_DIR / "sample.en.vtt"

    result = generate_transcript(subtitle_path, output_dir=tmp_path)

    assert result.success is True
    assert result.transcript_path is not None
    assert result.transcript_path.name == "sample.en.transcript.txt"


def test_output_dir_parameter_works_correctly(tmp_path: Path):
    subtitle_path = FIXTURES_DIR / "sample.en.vtt"
    custom_output_dir = tmp_path / "custom" / "output"

    result = generate_transcript(subtitle_path, output_dir=custom_output_dir)

    assert result.success is True
    assert result.transcript_path is not None
    assert result.transcript_path.parent == custom_output_dir
    assert result.transcript_path.exists()


def test_default_output_dir_is_subtitle_parent(tmp_path: Path):
    subtitle_path = tmp_path / "my_subtitle.vtt"
    subtitle_content = """WEBVTT

00:00:00.000 --> 00:00:01.000
Test content
"""
    subtitle_path.write_text(subtitle_content, encoding="utf-8")

    result = generate_transcript(subtitle_path)

    assert result.success is True
    assert result.transcript_path is not None
    assert result.transcript_path.parent == tmp_path


def test_empty_subtitle_file_returns_error(tmp_path: Path):
    subtitle_content = """WEBVTT

NOTE This is just a comment
"""
    subtitle_path = tmp_path / "empty.vtt"
    subtitle_path.write_text(subtitle_content, encoding="utf-8")

    result = generate_transcript(subtitle_path)

    assert result.success is False
    assert "No subtitle entries found" in result.error


def test_file_not_found_returns_error():
    result = generate_transcript(Path("/nonexistent/path/file.vtt"))

    assert result.success is False
    assert "No such file" in result.error or "No such file or directory" in result.error


def test_all_duplicates_returns_error(tmp_path: Path):
    subtitle_content = """WEBVTT

00:00:00.000 --> 00:00:01.000
Same line

00:00:01.100 --> 00:00:02.000
Same line

00:00:02.100 --> 00:00:03.000
Same line
"""
    subtitle_path = tmp_path / "all_dups.vtt"
    subtitle_path.write_text(subtitle_content, encoding="utf-8")

    result = generate_transcript(subtitle_path)

    assert result.success is True
    content = result.transcript_path.read_text(encoding="utf-8")
    assert content == "Same line"


def test_whitespace_only_entries_are_filtered(tmp_path: Path):
    subtitle_content = """WEBVTT

00:00:00.000 --> 00:00:01.000
Valid line

00:00:01.100 --> 00:00:02.000
   

00:00:02.100 --> 00:00:03.000
Another valid line
"""
    subtitle_path = tmp_path / "whitespace.vtt"
    subtitle_path.write_text(subtitle_content, encoding="utf-8")

    result = generate_transcript(subtitle_path)

    assert result.success is True
    assert result.transcript_path is not None
    content = result.transcript_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    assert lines == ["Valid line", "Another valid line"]
