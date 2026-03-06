from __future__ import annotations

from pathlib import Path

import pysubs2

from sublingo.core.models import BilingualEntry, SubtitleEntry
from sublingo.core.subtitle import (
    generate_bilingual_ass,
    is_auto_generated,
    parse_subtitle,
    write_ass,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_vtt_preserves_timestamps_and_text():
    entries = parse_subtitle(FIXTURES_DIR / "sample.en.vtt")

    assert entries == [
        SubtitleEntry(start_ms=1000, end_ms=3000, text="Hello world"),
        SubtitleEntry(start_ms=4500, end_ms=6000, text="This is a test."),
    ]


def test_parse_srt_preserves_timestamps_and_text():
    entries = parse_subtitle(FIXTURES_DIR / "sample.en.srt")

    assert entries == [
        SubtitleEntry(start_ms=1000, end_ms=3000, text="Hello world"),
        SubtitleEntry(start_ms=4500, end_ms=6000, text="This is a test."),
    ]


def test_parse_subtitle_handles_utf8_sig(tmp_path: Path):
    subtitle_path = tmp_path / "bom_sample.vtt"
    subtitle_path.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.500\n<c>Bom</c> sample\n",
        encoding="utf-8-sig",
    )

    entries = parse_subtitle(subtitle_path)

    assert entries == [SubtitleEntry(start_ms=1000, end_ms=2500, text="Bom sample")]


def test_is_auto_generated_detects_word_level_timestamps():
    entries = parse_subtitle(FIXTURES_DIR / "sample_auto.en.vtt")

    assert is_auto_generated(entries) is True


def test_is_auto_generated_keeps_sentence_level_subtitles_manual():
    entries = parse_subtitle(FIXTURES_DIR / "sample.en.vtt")

    assert is_auto_generated(entries) is False


def test_generate_bilingual_ass_contains_both_styles():
    ass_content = generate_bilingual_ass(
        [
            BilingualEntry(
                start_ms=0,
                end_ms=2000,
                original="Hello world",
                translated="你好，世界",
            )
        ],
        font_name="LXGWWenKai-Medium",
    )

    assert "Style: Primary" in ass_content
    assert "Style: Secondary" in ass_content
    assert "你好，世界" in ass_content
    assert "Hello world" in ass_content


def test_ass_output_is_valid_and_can_be_reparsed(tmp_path: Path):
    ass_content = generate_bilingual_ass(
        [
            BilingualEntry(
                start_ms=0,
                end_ms=2000,
                original="Hello",
                translated="你好",
            )
        ],
        font_name="LXGWWenKai-Medium",
    )
    output_path = tmp_path / "bilingual.ass"

    write_ass(ass_content, output_path)

    assert output_path.read_text(encoding="utf-8") == ass_content

    subtitles = pysubs2.SSAFile.from_string(ass_content)

    assert len(subtitles) == 2
    assert "Primary" in subtitles.styles
    assert "Secondary" in subtitles.styles
