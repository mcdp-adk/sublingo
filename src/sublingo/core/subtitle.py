from __future__ import annotations

import html
import re
from pathlib import Path

from sublingo.core.constants import (
    SUBTITLE_ASS_COLOR_BACK,
    SUBTITLE_ASS_COLOR_OUTLINE,
    SUBTITLE_ASS_COLOR_PRIMARY,
    SUBTITLE_ASS_COLOR_SECONDARY,
    SUBTITLE_ASS_FONT_SIZE_PRIMARY,
    SUBTITLE_ASS_FONT_SIZE_SECONDARY,
    SUBTITLE_ASS_MARGIN_LEFT,
    SUBTITLE_ASS_MARGIN_RIGHT,
    SUBTITLE_ASS_MARGIN_VERTICAL,
    SUBTITLE_ASS_OUTLINE_WIDTH,
    SUBTITLE_ASS_RESOLUTION_X,
    SUBTITLE_ASS_RESOLUTION_Y,
    SUBTITLE_ASS_SHADOW_DEPTH,
)
from sublingo.core.models import BilingualEntry, SubtitleEntry

SUPPORTED_SUBTITLE_EXTENSIONS: tuple[str, ...] = (".vtt", ".srt")

TIMESTAMP_PATTERN = r"(?:(\d{1,2}):)?(\d{2}):(\d{2})[.,](\d{3})"
TIMING_LINE_RE = re.compile(rf"{TIMESTAMP_PATTERN}\s*-->\s*{TIMESTAMP_PATTERN}")
HTML_TAG_RE = re.compile(r"<[^>]+>")
ASS_OVERRIDE_RE = re.compile(r"\{[^}]+\}")
WHITESPACE_RE = re.compile(r"\s+")

AUTO_MAX_DURATION_MS = 700
AUTO_MAX_WORDS_PER_ENTRY = 2
AUTO_SHORT_RATIO_THRESHOLD = 0.6
AUTO_WORD_RATIO_THRESHOLD = 0.6
AUTO_OVERLAP_RATIO_THRESHOLD = 0.3

ASS_ALIGNMENT_BOTTOM_CENTER = 2
ASS_BORDER_STYLE_OUTLINE = 1
ASS_ENCODING_UTF8 = 1
ASS_STYLE_SCALE = 100
ASS_WRAP_STYLE_SMART = 0
ASS_DEFAULT_LAYER = 0
ASS_SECONDARY_MARGIN_OFFSET = SUBTITLE_ASS_FONT_SIZE_PRIMARY


def parse_subtitle(path: Path) -> list[SubtitleEntry]:
    content = path.read_text(encoding="utf-8-sig")
    suffix = path.suffix.lower()

    if suffix == ".vtt":
        return _parse_vtt(content)
    if suffix == ".srt":
        return _parse_srt(content)

    supported = ", ".join(SUPPORTED_SUBTITLE_EXTENSIONS)
    raise ValueError(f"Unsupported subtitle format: {suffix} (supported: {supported})")


def is_auto_generated(entries: list[SubtitleEntry]) -> bool:
    if len(entries) < 2:
        return False

    short_entries = 0
    word_like_entries = 0
    overlapping_pairs = 0

    for index, entry in enumerate(entries):
        duration_ms = entry.end_ms - entry.start_ms
        if duration_ms <= AUTO_MAX_DURATION_MS:
            short_entries += 1
        if len(entry.text.split()) <= AUTO_MAX_WORDS_PER_ENTRY:
            word_like_entries += 1
        if index < len(entries) - 1 and entries[index + 1].start_ms < entry.end_ms:
            overlapping_pairs += 1

    entry_count = len(entries)
    pair_count = entry_count - 1
    short_ratio = short_entries / entry_count
    word_ratio = word_like_entries / entry_count
    overlap_ratio = overlapping_pairs / pair_count

    return short_ratio >= AUTO_SHORT_RATIO_THRESHOLD and (
        word_ratio >= AUTO_WORD_RATIO_THRESHOLD
        or overlap_ratio >= AUTO_OVERLAP_RATIO_THRESHOLD
    )


def generate_bilingual_ass(
    entries: list[BilingualEntry],
    *,
    font_name: str,
    resolution: tuple[int, int] = (
        SUBTITLE_ASS_RESOLUTION_X,
        SUBTITLE_ASS_RESOLUTION_Y,
    ),
) -> str:
    resolution_x, resolution_y = resolution
    secondary_margin = SUBTITLE_ASS_MARGIN_VERTICAL + ASS_SECONDARY_MARGIN_OFFSET
    sections = [
        "[Script Info]",
        "Title: Bilingual Subtitles",
        "ScriptType: v4.00+",
        f"PlayResX: {resolution_x}",
        f"PlayResY: {resolution_y}",
        f"WrapStyle: {ASS_WRAP_STYLE_SMART}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        (
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding"
        ),
        _build_style_line(
            name="Primary",
            font_name=font_name,
            font_size=SUBTITLE_ASS_FONT_SIZE_PRIMARY,
            margin_vertical=SUBTITLE_ASS_MARGIN_VERTICAL,
        ),
        _build_style_line(
            name="Secondary",
            font_name=font_name,
            font_size=SUBTITLE_ASS_FONT_SIZE_SECONDARY,
            margin_vertical=secondary_margin,
        ),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for entry in entries:
        start = _format_ass_timestamp(entry.start_ms)
        end = _format_ass_timestamp(entry.end_ms)
        translated = _escape_ass_text(entry.translated)
        original = _escape_ass_text(entry.original)

        if translated:
            sections.append(
                f"Dialogue: {ASS_DEFAULT_LAYER},{start},{end},Primary,,0,0,0,,{translated}"
            )
        if original:
            sections.append(
                f"Dialogue: {ASS_DEFAULT_LAYER},{start},{end},Secondary,,0,0,0,,{original}"
            )

    return "\n".join(sections) + "\n"


def write_ass(content: str, path: Path) -> None:
    path.write_text(content, encoding="utf-8")


def _parse_vtt(content: str) -> list[SubtitleEntry]:
    entries: list[SubtitleEntry] = []

    for block in _split_blocks(content):
        lines = _non_empty_lines(block)
        if not lines or lines[0] == "WEBVTT" or lines[0].startswith("NOTE"):
            continue

        timing_index = _find_timing_line_index(lines)
        if timing_index < 0:
            continue

        start_ms, end_ms = _parse_timing_line(lines[timing_index])
        text = _clean_text(" ".join(lines[timing_index + 1 :]), strip_html_tags=True)
        if text:
            entries.append(SubtitleEntry(start_ms=start_ms, end_ms=end_ms, text=text))

    return entries


def _parse_srt(content: str) -> list[SubtitleEntry]:
    entries: list[SubtitleEntry] = []

    for block in _split_blocks(content):
        lines = _non_empty_lines(block)
        if not lines:
            continue

        timing_index = _find_timing_line_index(lines)
        if timing_index < 0:
            continue

        start_ms, end_ms = _parse_timing_line(lines[timing_index])
        text = _clean_text(" ".join(lines[timing_index + 1 :]), strip_html_tags=False)
        if text:
            entries.append(SubtitleEntry(start_ms=start_ms, end_ms=end_ms, text=text))

    return entries


def _split_blocks(content: str) -> list[str]:
    return re.split(r"\r?\n\r?\n", content.lstrip("\ufeff"))


def _non_empty_lines(block: str) -> list[str]:
    return [line.strip() for line in re.split(r"\r?\n", block) if line.strip()]


def _find_timing_line_index(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        if "-->" in line:
            return index
    return -1


def _parse_timing_line(line: str) -> tuple[int, int]:
    match = TIMING_LINE_RE.search(line)
    if match is None:
        raise ValueError(f"Invalid subtitle timing line: {line}")
    return _match_groups_to_ms(match, 1), _match_groups_to_ms(match, 5)


def _match_groups_to_ms(match: re.Match[str], offset: int) -> int:
    hours = int(match.group(offset) or 0)
    minutes = int(match.group(offset + 1))
    seconds = int(match.group(offset + 2))
    milliseconds = int(match.group(offset + 3))
    return (((hours * 60) + minutes) * 60 + seconds) * 1000 + milliseconds


def _clean_text(text: str, *, strip_html_tags: bool) -> str:
    cleaned = text
    if strip_html_tags:
        cleaned = HTML_TAG_RE.sub("", cleaned)
    cleaned = ASS_OVERRIDE_RE.sub("", cleaned)
    cleaned = html.unescape(cleaned)
    return WHITESPACE_RE.sub(" ", cleaned).strip()


def _build_style_line(
    *,
    name: str,
    font_name: str,
    font_size: int,
    margin_vertical: int,
) -> str:
    return (
        f"Style: {name},{font_name},{font_size},{SUBTITLE_ASS_COLOR_PRIMARY},"
        f"{SUBTITLE_ASS_COLOR_SECONDARY},{SUBTITLE_ASS_COLOR_OUTLINE},"
        f"{SUBTITLE_ASS_COLOR_BACK},0,0,0,0,{ASS_STYLE_SCALE},{ASS_STYLE_SCALE},"
        f"0,0,{ASS_BORDER_STYLE_OUTLINE},{SUBTITLE_ASS_OUTLINE_WIDTH},"
        f"{SUBTITLE_ASS_SHADOW_DEPTH},{ASS_ALIGNMENT_BOTTOM_CENTER},"
        f"{SUBTITLE_ASS_MARGIN_LEFT},{SUBTITLE_ASS_MARGIN_RIGHT},"
        f"{margin_vertical},{ASS_ENCODING_UTF8}"
    )


def _format_ass_timestamp(milliseconds: int) -> str:
    total_seconds, remainder_ms = divmod(milliseconds, 1000)
    hours, remainder_seconds = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder_seconds, 60)
    centiseconds = remainder_ms // 10
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def _escape_ass_text(text: str) -> str:
    escaped = text.replace("\\", "\\\\")
    escaped = escaped.replace("{", r"\{")
    return escaped.replace("}", r"\}")
