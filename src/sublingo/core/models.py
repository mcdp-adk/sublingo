"""All data models and ProgressCallback protocol for sublingo."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProgressCallback(Protocol):
    """Protocol for progress reporting during long-running operations.

    ``on_progress`` accepts optional keyword arguments via *meta* to carry
    structured data such as download speed, ETA, stage info, and batch
    progress.

    ``on_log`` accepts an optional *detail* string for verbose information.
    """

    def on_progress(
        self, current: int, total: int, message: str = "", **meta: Any
    ) -> None:
        """Report progress of an operation.

        Args:
            current: Current progress value.
            total: Total progress value.
            message: Optional message describing current state.
            **meta: Additional metadata (speed, ETA, etc.).
        """
        ...

    def on_log(self, level: str, message: str, detail: str = "") -> None:
        """Log a message.

        Args:
            level: Log level (debug, info, warning, error).
            message: Log message.
            detail: Optional detailed information.
        """
        ...


@dataclass
class VideoInfo:
    """Information about a video."""

    url: str
    video_id: str
    title: str
    duration: int
    channel: str
    upload_date: str
    thumbnail_url: str
    view_count: int
    available_subtitles: dict[str, list[str]]
    available_auto_captions: dict[str, list[str]]


@dataclass
class DownloadResult:
    """Result of video download operation."""

    success: bool
    video_path: Path | None = None
    subtitle_paths: list[Path] = field(default_factory=list)
    video_title: str = ""
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class TranslateResult:
    """Result of subtitle translation operation."""

    success: bool
    output_path: Path | None = None
    source_lang: str = ""
    target_lang: str = ""
    entry_count: int = 0
    failed_count: int = 0
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class FontSubsetResult:
    """Result of font subsetting operation."""

    success: bool
    output_path: Path | None = None
    original_size: int = 0
    subset_size: int = 0
    char_count: int = 0
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class TranscriptResult:
    """Result of transcript generation operation."""

    success: bool
    transcript_path: Path | None = None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class MuxResult:
    """Result of subtitle muxing operation (softsub)."""

    success: bool
    output_path: Path | None = None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class BurnResult:
    """Result of subtitle burning operation (hardsub)."""

    success: bool
    output_path: Path | None = None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class StreamInfo:
    """Information about a media stream."""

    index: int
    codec_type: str
    codec_name: str
    language: str | None = None
    title: str | None = None


@dataclass
class ProjectStatus:
    """Status of a project at a given point in time."""

    has_video: bool = False
    has_subtitle: bool = False
    has_translated: bool = False
    has_font: bool = False
    has_final: bool = False
    next_stage: str = ""


@dataclass
class WorkflowResult:
    """Result of a complete workflow execution."""

    success: bool
    current_stage: str = ""
    download: DownloadResult | None = None
    translate: TranslateResult | None = None
    font: FontSubsetResult | None = None
    mux: MuxResult | None = None
    video_title: str = ""
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class SubtitleEntry:
    """A single subtitle entry/timing."""

    start_ms: int
    end_ms: int
    text: str


@dataclass
class BilingualEntry:
    """A bilingual subtitle entry with original and translated text."""

    start_ms: int
    end_ms: int
    original: str
    translated: str
