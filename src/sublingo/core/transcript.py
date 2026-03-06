"""Subtitle-to-transcript converter.

Converts VTT/SRT subtitle files into plain-text transcripts by:
1. Loading and parsing the subtitle file
2. Deduplicating consecutive repeated entries
3. Writing UTF-8 output
"""

from __future__ import annotations

from pathlib import Path

from sublingo.core.models import SubtitleEntry, TranscriptResult
from sublingo.core.subtitle import parse_subtitle


def _deduplicate_entries(entries: list[SubtitleEntry]) -> list[SubtitleEntry]:
    """Remove consecutive duplicate entries and entries with empty text.

    Two entries are considered duplicates when their stripped text is identical.
    Empty (whitespace-only) entries are always removed.
    """
    result: list[SubtitleEntry] = []

    for entry in entries:
        stripped = entry.text.strip()
        if not stripped:
            continue
        if result and result[-1].text.strip() == stripped:
            continue
        result.append(entry)

    return result


def generate_transcript(
    subtitle_path: Path,
    *,
    output_dir: Path | None = None,
) -> TranscriptResult:
    """Generate a plain-text transcript from a subtitle file.

    Steps:
    1. Load the subtitle file (VTT or SRT) via :func:`parse_subtitle`.
    2. Deduplicate consecutive repeated entries.
    3. Write the transcript to ``{input_stem}.transcript.txt``.

    Parameters
    ----------
    subtitle_path:
        Path to the subtitle file (VTT or SRT).
    output_dir:
        Optional output directory. If not provided, uses the parent
        directory of *subtitle_path*.

    Returns
    -------
    TranscriptResult
        On success, *transcript_path* points to the written file.
    """
    try:
        entries = parse_subtitle(subtitle_path)

        if not entries:
            return TranscriptResult(
                success=False,
                error="No subtitle entries found in the file.",
            )

        # Deduplicate consecutive repeated entries
        deduped = _deduplicate_entries(entries)

        if not deduped:
            return TranscriptResult(
                success=False,
                error="All subtitle entries were empty or duplicates.",
            )

        # Join text with newlines
        text = "\n".join(entry.text.strip() for entry in deduped)

        # Determine output path
        out_dir = output_dir or subtitle_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{subtitle_path.stem}.transcript.txt"
        output_path.write_text(text, encoding="utf-8")

        return TranscriptResult(success=True, transcript_path=output_path)

    except FileNotFoundError as exc:
        return TranscriptResult(success=False, error=str(exc))
    except ValueError as exc:
        return TranscriptResult(success=False, error=str(exc))
    except Exception as exc:
        return TranscriptResult(success=False, error=f"Unexpected error: {exc}")
