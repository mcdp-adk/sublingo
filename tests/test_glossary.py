from __future__ import annotations

from pathlib import Path

import pytest

from sublingo.core.glossary import format_glossary_for_prompt, load_glossary


def test_load_glossary_reads_source_target_columns(tmp_path: Path):
    glossary = tmp_path / "glossary.csv"
    glossary.write_text(
        "source,target,note\nhello,你好,greeting\nworld,世界,noun\n",
        encoding="utf-8",
    )

    entries = load_glossary(glossary)

    assert entries == [("hello", "你好"), ("world", "世界")]


def test_load_glossary_skips_empty_values(tmp_path: Path):
    glossary = tmp_path / "glossary.csv"
    glossary.write_text(
        "source,target\nhello,\n,世界\nbook,书\n",
        encoding="utf-8",
    )

    entries = load_glossary(glossary)

    assert entries == [("book", "书")]


def test_load_glossary_missing_file_raises_error(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_glossary(tmp_path / "missing.csv")


def test_format_glossary_for_prompt_returns_empty_on_no_entries():
    assert format_glossary_for_prompt([]) == ""


def test_format_glossary_for_prompt_formats_lines():
    text = format_glossary_for_prompt([("cloud", "云"), ("AI", "人工智能")])

    assert "Glossary terms" in text
    assert "- cloud => 云" in text
    assert "- AI => 人工智能" in text
