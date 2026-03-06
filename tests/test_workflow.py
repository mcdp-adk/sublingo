from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sublingo.core.config import AppConfig
from sublingo.core.models import (
    DownloadResult,
    FontSubsetResult,
    MuxResult,
    ProjectStatus,
    TranslateResult,
    VideoInfo,
)
from sublingo.core.workflow import (
    detect_project_status,
    resume_workflow,
    run_workflow,
)


class ProgressSpy:
    def __init__(self) -> None:
        self.events: list[tuple[int, int, str, dict[str, Any]]] = []

    def on_progress(
        self,
        current: int,
        total: int,
        message: str = "",
        **meta: Any,
    ) -> None:
        self.events.append((current, total, message, meta))

    def on_log(self, level: str, message: str, detail: str = "") -> None:
        return None


def make_config(*, generate_transcript: bool = False) -> AppConfig:
    return AppConfig(
        target_language="zh-Hans",
        generate_transcript=generate_transcript,
        font_file="TestFont.ttf",
        ai_api_key="token",
    )


@pytest.mark.asyncio
async def test_run_workflow_full_pipeline_stage_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    calls: list[str] = []
    output_dir = tmp_path / "output"
    font_dir = tmp_path / "fonts"
    font_dir.mkdir(parents=True)
    (font_dir / "TestFont.ttf").write_text("font", encoding="utf-8")
    spy = ProgressSpy()

    monkeypatch.setattr(
        "sublingo.core.workflow.extract_info",
        lambda *args, **kwargs: VideoInfo(
            url="https://example.com/v",
            video_id="abc123",
            title="Demo Video",
            duration=1,
            channel="c",
            upload_date="20260101",
            thumbnail_url="",
            view_count=1,
            available_subtitles={},
            available_auto_captions={},
        ),
    )

    def fake_download(*args, **kwargs):
        calls.append("download")
        project_dir = kwargs["output_dir"]
        video = project_dir / "video.mp4"
        subtitle = project_dir / "video.sub-en.vtt"
        video.write_text("v", encoding="utf-8")
        subtitle.write_text("WEBVTT", encoding="utf-8")
        return DownloadResult(
            success=True,
            video_path=video,
            subtitle_paths=[subtitle],
            video_title="Demo Video",
        )

    async def fake_translate(*args, **kwargs):
        calls.append("translate")
        output_path = kwargs["output_dir"] / "video.sub-en.zh-Hans.ass"
        output_path.write_text("ass", encoding="utf-8")
        return TranslateResult(success=True, output_path=output_path)

    def fake_subset_font(*args, **kwargs):
        calls.append("font")
        output_path = kwargs["output_dir"] / "video.sub-en.zh-Hans.TestFont.ttf"
        output_path.write_text("f", encoding="utf-8")
        return FontSubsetResult(success=True, output_path=output_path)

    def fake_softsub(*args, **kwargs):
        calls.append("mux")
        output_path = kwargs["output_dir"] / "video.softsub.mkv"
        output_path.write_text("m", encoding="utf-8")
        return MuxResult(success=True, output_path=output_path)

    def fake_transcript(*args, **kwargs):
        calls.append("transcript")
        transcript = kwargs["output_dir"] / "video.sub-en.transcript.txt"
        transcript.write_text("t", encoding="utf-8")
        return type("Result", (), {"success": True, "error": None})()

    monkeypatch.setattr("sublingo.core.workflow.download", fake_download)
    monkeypatch.setattr("sublingo.core.workflow.translate", fake_translate)
    monkeypatch.setattr("sublingo.core.workflow.subset_font", fake_subset_font)
    monkeypatch.setattr("sublingo.core.workflow.softsub", fake_softsub)
    monkeypatch.setattr("sublingo.core.workflow.generate_transcript", fake_transcript)

    result = await run_workflow(
        "https://example.com/v",
        config=make_config(generate_transcript=True),
        cookie_file=tmp_path / "cookies.txt",
        font_dir=font_dir,
        output_dir=output_dir,
        progress=spy,
    )

    assert result.success is True
    assert result.current_stage == "complete"
    assert calls == ["download", "translate", "font", "mux", "transcript"]

    project_dir = output_dir / "[abc123]Demo Video"
    assert project_dir.exists() is True

    stage_flow = [(e[2], e[3].get("stage_status")) for e in spy.events]
    assert stage_flow == [
        ("download", "active"),
        ("download", "done"),
        ("translate", "active"),
        ("translate", "done"),
        ("font", "active"),
        ("font", "done"),
        ("mux", "active"),
        ("mux", "done"),
        ("transcript", "active"),
        ("transcript", "done"),
    ]


@pytest.mark.asyncio
async def test_run_workflow_skips_stages_with_existing_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    output_dir = tmp_path / "output"
    project_dir = output_dir / "[abc123]Demo Video"
    project_dir.mkdir(parents=True)
    (project_dir / "video.mp4").write_text("v", encoding="utf-8")
    (project_dir / "video.sub-en.vtt").write_text("WEBVTT", encoding="utf-8")
    (project_dir / "video.sub-en.zh-Hans.ass").write_text("ass", encoding="utf-8")
    (project_dir / "video.sub-en.zh-Hans.TestFont.ttf").write_text(
        "ttf", encoding="utf-8"
    )

    monkeypatch.setattr(
        "sublingo.core.workflow.extract_info",
        lambda *args, **kwargs: VideoInfo(
            url="https://example.com/v",
            video_id="abc123",
            title="Demo Video",
            duration=1,
            channel="c",
            upload_date="20260101",
            thumbnail_url="",
            view_count=1,
            available_subtitles={},
            available_auto_captions={},
        ),
    )
    monkeypatch.setattr(
        "sublingo.core.workflow.download",
        lambda *args, **kwargs: pytest.fail("download should be skipped"),
    )
    monkeypatch.setattr(
        "sublingo.core.workflow.translate",
        lambda *args, **kwargs: pytest.fail("translate should be skipped"),
    )
    monkeypatch.setattr(
        "sublingo.core.workflow.subset_font",
        lambda *args, **kwargs: pytest.fail("font should be skipped"),
    )

    mux_called = {"value": False}

    def fake_softsub(*args, **kwargs):
        mux_called["value"] = True
        out = kwargs["output_dir"] / "video.softsub.mkv"
        out.write_text("m", encoding="utf-8")
        return MuxResult(success=True, output_path=out)

    monkeypatch.setattr("sublingo.core.workflow.softsub", fake_softsub)

    result = await run_workflow(
        "https://example.com/v",
        config=make_config(),
        cookie_file=tmp_path / "cookies.txt",
        output_dir=output_dir,
    )

    assert result.success is True
    assert mux_called["value"] is True


@pytest.mark.asyncio
async def test_run_workflow_failure_in_stage_returns_failed_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    output_dir = tmp_path / "output"

    monkeypatch.setattr(
        "sublingo.core.workflow.extract_info",
        lambda *args, **kwargs: VideoInfo(
            url="https://example.com/v",
            video_id="abc123",
            title="Demo Video",
            duration=1,
            channel="c",
            upload_date="20260101",
            thumbnail_url="",
            view_count=1,
            available_subtitles={},
            available_auto_captions={},
        ),
    )

    def fake_download(*args, **kwargs):
        project_dir = kwargs["output_dir"]
        video = project_dir / "video.mp4"
        subtitle = project_dir / "video.sub-en.vtt"
        video.write_text("v", encoding="utf-8")
        subtitle.write_text("WEBVTT", encoding="utf-8")
        return DownloadResult(success=True, video_path=video, subtitle_paths=[subtitle])

    async def fake_translate(*args, **kwargs):
        return TranslateResult(success=False, error="ai failed")

    monkeypatch.setattr("sublingo.core.workflow.download", fake_download)
    monkeypatch.setattr("sublingo.core.workflow.translate", fake_translate)

    result = await run_workflow(
        "https://example.com/v",
        config=make_config(),
        cookie_file=tmp_path / "cookies.txt",
        output_dir=output_dir,
    )

    assert result.success is False
    assert result.current_stage == "translate"
    assert result.error == "Translate failed: ai failed"


def test_detect_project_status_detects_complete_state(tmp_path: Path):
    (tmp_path / "video.mp4").write_text("v", encoding="utf-8")
    (tmp_path / "video.sub-en.vtt").write_text("WEBVTT", encoding="utf-8")
    (tmp_path / "video.sub-en.zh-Hans.ass").write_text("ass", encoding="utf-8")
    (tmp_path / "video.sub-en.zh-Hans.TestFont.ttf").write_text("ttf", encoding="utf-8")
    (tmp_path / "video.softsub.mkv").write_text("m", encoding="utf-8")

    status = detect_project_status(tmp_path)

    assert isinstance(status, ProjectStatus)
    assert status.has_video is True
    assert status.has_subtitle is True
    assert status.has_translated is True
    assert status.has_font is True
    assert status.has_final is True
    assert status.next_stage == "complete"


@pytest.mark.asyncio
async def test_resume_workflow_starts_from_detected_stage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    project_dir = tmp_path / "[abc123]Demo Video"
    project_dir.mkdir(parents=True)
    (project_dir / "video.mp4").write_text("v", encoding="utf-8")
    (project_dir / "video.sub-en.vtt").write_text("WEBVTT", encoding="utf-8")
    (project_dir / "video.sub-en.zh-Hans.ass").write_text("ass", encoding="utf-8")

    monkeypatch.setattr(
        "sublingo.core.workflow.download",
        lambda *args, **kwargs: pytest.fail("download should not run on resume"),
    )
    monkeypatch.setattr(
        "sublingo.core.workflow.translate",
        lambda *args, **kwargs: pytest.fail("translate should not run on resume"),
    )

    called = []

    def fake_subset_font(*args, **kwargs):
        called.append("font")
        out = kwargs["output_dir"] / "video.sub-en.zh-Hans.TestFont.ttf"
        out.write_text("ttf", encoding="utf-8")
        return FontSubsetResult(success=True, output_path=out)

    def fake_softsub(*args, **kwargs):
        called.append("mux")
        out = kwargs["output_dir"] / "video.softsub.mkv"
        out.write_text("m", encoding="utf-8")
        return MuxResult(success=True, output_path=out)

    font_dir = tmp_path / "fonts"
    font_dir.mkdir(parents=True)
    (font_dir / "TestFont.ttf").write_text("font", encoding="utf-8")

    monkeypatch.setattr("sublingo.core.workflow.subset_font", fake_subset_font)
    monkeypatch.setattr("sublingo.core.workflow.softsub", fake_softsub)

    result = await resume_workflow(
        project_dir,
        config=make_config(),
        cookie_file=tmp_path / "cookies.txt",
        font_dir=font_dir,
        output_dir=tmp_path,
    )

    assert result.success is True
    assert called == ["font", "mux"]
