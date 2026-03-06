from __future__ import annotations

from pathlib import Path

from fontTools.ttLib import TTFont

from sublingo.core.font import _extract_chars, subset_font

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FONTS_DIR = Path(__file__).parent.parent / "fonts"
REGULAR_FONT_PATH = FONTS_DIR / "LXGWWenKai-Regular.ttf"

POSTSCRIPT_NAME_ID = 6
TT_NAME_PLATFORM_ID = 3
TT_NAME_ENCODING_ID = 1
TT_NAME_LANGUAGE_ID = 0x409


def test_subset_font_creates_smaller_font_than_original(tmp_path: Path):
    result = subset_font(
        FIXTURES_DIR / "sample.en.srt",
        REGULAR_FONT_PATH,
        output_dir=tmp_path,
    )

    assert result.success is True
    assert result.output_path is not None
    assert result.output_path.exists()
    assert result.subset_size < result.original_size


def test_subset_font_contains_all_characters_from_subtitle(tmp_path: Path):
    subtitle_path = tmp_path / "tagged.srt"
    subtitle_path.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\n{\\i1}Hello{\\i0} 你好\n",
        encoding="utf-8",
    )

    result = subset_font(subtitle_path, REGULAR_FONT_PATH, output_dir=tmp_path)

    assert result.success is True
    assert result.output_path is not None
    assert _extract_chars(subtitle_path) == {"H", "e", "l", "o", "你", "好"}
    assert _font_contains_chars(result.output_path, {"H", "e", "l", "o", "你", "好"})


def test_subset_font_uses_expected_output_file_naming(tmp_path: Path):
    result = subset_font(
        FIXTURES_DIR / "sample.en.srt",
        REGULAR_FONT_PATH,
        output_dir=tmp_path,
    )

    assert result.success is True
    assert result.output_path is not None
    assert (
        result.output_path.name
        == f"sample.en.{_get_postscript_name(REGULAR_FONT_PATH)}.ttf"
    )


def test_empty_subtitle_produces_minimal_subset(tmp_path: Path):
    subtitle_path = tmp_path / "empty.srt"
    subtitle_path.write_text("", encoding="utf-8")

    result = subset_font(subtitle_path, REGULAR_FONT_PATH, output_dir=tmp_path)

    assert result.success is True
    assert result.output_path is not None
    assert result.char_count == 0
    assert result.subset_size < result.original_size
    assert _font_contains_chars(result.output_path, {"A"}) is False


def test_subset_font_preserves_cjk_characters(tmp_path: Path):
    subtitle_path = tmp_path / "cjk.srt"
    subtitle_path.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\n你好世界\n",
        encoding="utf-8",
    )

    result = subset_font(subtitle_path, REGULAR_FONT_PATH, output_dir=tmp_path)

    assert result.success is True
    assert result.output_path is not None
    assert result.char_count == 4
    assert _font_contains_chars(result.output_path, {"你", "好", "世", "界"})


def _font_contains_chars(font_path: Path, chars: set[str]) -> bool:
    with TTFont(font_path) as font:
        cmap = font.getBestCmap()
    if cmap is None:
        return False
    return all(ord(char) in cmap for char in chars)


def _get_postscript_name(font_path: Path) -> str:
    with TTFont(font_path) as font:
        name = font["name"].getName(
            POSTSCRIPT_NAME_ID,
            TT_NAME_PLATFORM_ID,
            TT_NAME_ENCODING_ID,
            TT_NAME_LANGUAGE_ID,
        )
    if name is None:
        return font_path.stem
    return name.toUnicode()
