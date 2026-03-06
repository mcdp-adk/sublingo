from __future__ import annotations

from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

from sublingo.core.models import FontSubsetResult
from sublingo.core.subtitle import parse_subtitle

MIN_PRINTABLE_CODEPOINT = 0x20
POSTSCRIPT_NAME_ID = 6
TT_NAME_PLATFORM_ID = 3
TT_NAME_ENCODING_ID = 1
TT_NAME_LANGUAGE_ID = 0x409
TTF_SUFFIX = ".ttf"


def subset_font(
    subtitle_path: Path,
    font_path: Path,
    *,
    output_dir: Path | None = None,
) -> FontSubsetResult:
    if not font_path.exists():
        return FontSubsetResult(
            success=False, error=f"Font file not found: {font_path}"
        )

    target_dir = output_dir or subtitle_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        chars = _extract_chars(subtitle_path)
        original_size = font_path.stat().st_size

        with TTFont(font_path) as font:
            font_name = _get_font_name(font, font_path)
            output_path = target_dir / f"{subtitle_path.stem}.{font_name}{TTF_SUFFIX}"

            options = Options()
            options.layout_features = ["*"]
            options.notdef_outline = True

            subsetter = Subsetter(options=options)
            subsetter.populate(text="".join(sorted(chars)))
            subsetter.subset(font)
            font.save(output_path)

        subset_size = output_path.stat().st_size
    except Exception as exc:  # noqa: BLE001
        return FontSubsetResult(success=False, error=str(exc))

    return FontSubsetResult(
        success=True,
        output_path=output_path,
        original_size=original_size,
        subset_size=subset_size,
        char_count=len(chars),
    )


def _extract_chars(subtitle_path: Path) -> set[str]:
    text_segments = [entry.text for entry in parse_subtitle(subtitle_path)]
    joined_text = "".join(text_segments)
    return {char for char in joined_text if ord(char) > MIN_PRINTABLE_CODEPOINT}


def _get_font_name(font: TTFont, font_path: Path) -> str:
    name_table = font["name"]
    font_name = name_table.getName(
        POSTSCRIPT_NAME_ID,
        TT_NAME_PLATFORM_ID,
        TT_NAME_ENCODING_ID,
        TT_NAME_LANGUAGE_ID,
    )
    if font_name is None:
        font_name = name_table.getName(POSTSCRIPT_NAME_ID, 1, 0, 0)
    if font_name is None:
        return font_path.stem
    return font_name.toUnicode()
