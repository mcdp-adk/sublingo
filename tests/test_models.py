"""Tests for core data models."""

from __future__ import annotations

from pathlib import Path

import pytest

from sublingo.core.models import (
    BilingualEntry,
    BurnResult,
    DownloadResult,
    FontSubsetResult,
    MuxResult,
    ProgressCallback,
    ProjectStatus,
    StreamInfo,
    SubtitleEntry,
    TranscriptResult,
    TranslateResult,
    VideoInfo,
    WorkflowResult,
)


class TestProgressCallback:
    """Test ProgressCallback protocol compliance."""

    def test_progress_callback_can_be_implemented(self):
        """Test that ProgressCallback can be implemented by a class."""

        class DummyCallback:
            def on_progress(self, current, total, message="", **meta):
                pass

            def on_log(self, level, message, detail=""):
                pass

        callback = DummyCallback()
        assert isinstance(callback, ProgressCallback)


class TestVideoInfo:
    """Test VideoInfo dataclass."""

    def test_video_info_creation(self):
        """Test creating a VideoInfo instance."""
        info = VideoInfo(
            url="https://youtube.com/watch?v=test123",
            video_id="test123",
            title="Test Video",
            duration=300,
            channel="Test Channel",
            upload_date="2024-01-01",
            thumbnail_url="https://example.com/thumb.jpg",
            view_count=1000,
            available_subtitles={"en": ["en-US"]},
            available_auto_captions={"es": ["es-ES"]},
        )
        assert info.video_id == "test123"
        assert info.title == "Test Video"
        assert info.duration == 300


class TestDownloadResult:
    """Test DownloadResult dataclass."""

    def test_download_result_success(self):
        """Test successful download result."""
        result = DownloadResult(
            success=True,
            video_path=Path("/tmp/video.mp4"),
            subtitle_paths=[Path("/tmp/sub.srt")],
            video_title="Test",
        )
        assert result.success is True
        assert result.video_path == Path("/tmp/video.mp4")

    def test_download_result_failure(self):
        """Test failed download result."""
        result = DownloadResult(
            success=False,
            error="Network error",
            warnings=["Slow connection"],
        )
        assert result.success is False
        assert result.error == "Network error"
        assert result.warnings == ["Slow connection"]

    def test_download_result_default_warnings(self):
        """Test that warnings defaults to empty list."""
        result = DownloadResult(success=True)
        assert result.warnings == []


class TestTranslateResult:
    """Test TranslateResult dataclass."""

    def test_translate_result_creation(self):
        """Test creating TranslateResult."""
        result = TranslateResult(
            success=True,
            output_path=Path("/tmp/output.ass"),
            source_lang="en",
            target_lang="zh",
            entry_count=100,
            failed_count=2,
        )
        assert result.success is True
        assert result.source_lang == "en"
        assert result.target_lang == "zh"
        assert result.entry_count == 100
        assert result.failed_count == 2


class TestFontSubsetResult:
    """Test FontSubsetResult dataclass."""

    def test_font_subset_result_creation(self):
        """Test creating FontSubsetResult."""
        result = FontSubsetResult(
            success=True,
            output_path=Path("/tmp/font.subset.ttf"),
            original_size=1024000,
            subset_size=20480,
            char_count=3000,
        )
        assert result.success is True
        assert result.original_size == 1024000
        assert result.subset_size == 20480
        assert result.char_count == 3000


class TestTranscriptResult:
    """Test TranscriptResult dataclass."""

    def test_transcript_result_creation(self):
        """Test creating TranscriptResult."""
        result = TranscriptResult(
            success=True,
            transcript_path=Path("/tmp/transcript.txt"),
        )
        assert result.success is True
        assert result.transcript_path == Path("/tmp/transcript.txt")


class TestMuxResult:
    """Test MuxResult dataclass."""

    def test_mux_result_creation(self):
        """Test creating MuxResult."""
        result = MuxResult(
            success=True,
            output_path=Path("/tmp/output.mkv"),
        )
        assert result.success is True
        assert result.output_path == Path("/tmp/output.mkv")


class TestBurnResult:
    """Test BurnResult dataclass."""

    def test_burn_result_creation(self):
        """Test creating BurnResult."""
        result = BurnResult(
            success=True,
            output_path=Path("/tmp/output.mp4"),
        )
        assert result.success is True
        assert result.output_path == Path("/tmp/output.mp4")


class TestStreamInfo:
    """Test StreamInfo dataclass."""

    def test_stream_info_creation(self):
        """Test creating StreamInfo."""
        info = StreamInfo(
            index=0,
            codec_type="video",
            codec_name="h264",
            language="eng",
            title="Main Video",
        )
        assert info.index == 0
        assert info.codec_type == "video"
        assert info.language == "eng"

    def test_stream_info_optional_fields(self):
        """Test StreamInfo with optional fields as None."""
        info = StreamInfo(
            index=1,
            codec_type="audio",
            codec_name="aac",
        )
        assert info.language is None
        assert info.title is None


class TestProjectStatus:
    """Test ProjectStatus dataclass."""

    def test_project_status_defaults(self):
        """Test ProjectStatus with default values."""
        status = ProjectStatus()
        assert status.has_video is False
        assert status.has_subtitle is False
        assert status.has_translated is False
        assert status.has_font is False
        assert status.has_final is False
        assert status.next_stage == ""

    def test_project_status_creation(self):
        """Test creating ProjectStatus with values."""
        status = ProjectStatus(
            has_video=True,
            has_subtitle=True,
            next_stage="translate",
        )
        assert status.has_video is True
        assert status.has_subtitle is True
        assert status.next_stage == "translate"


class TestWorkflowResult:
    """Test WorkflowResult dataclass."""

    def test_workflow_result_creation(self):
        """Test creating WorkflowResult."""
        download_result = DownloadResult(success=True)
        result = WorkflowResult(
            success=True,
            current_stage="download",
            download=download_result,
            video_title="Test Video",
        )
        assert result.success is True
        assert result.current_stage == "download"
        assert result.download is download_result

    def test_workflow_result_default_warnings(self):
        """Test that warnings defaults to empty list."""
        result = WorkflowResult(success=False)
        assert result.warnings == []


class TestSubtitleEntry:
    """Test SubtitleEntry dataclass."""

    def test_subtitle_entry_creation(self):
        """Test creating SubtitleEntry."""
        entry = SubtitleEntry(
            start_ms=1000,
            end_ms=3000,
            text="Hello world",
        )
        assert entry.start_ms == 1000
        assert entry.end_ms == 3000
        assert entry.text == "Hello world"


class TestBilingualEntry:
    """Test BilingualEntry dataclass."""

    def test_bilingual_entry_creation(self):
        """Test creating BilingualEntry."""
        entry = BilingualEntry(
            start_ms=1000,
            end_ms=3000,
            original="Hello",
            translated="你好",
        )
        assert entry.start_ms == 1000
        assert entry.end_ms == 3000
        assert entry.original == "Hello"
        assert entry.translated == "你好"
