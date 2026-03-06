from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sublingo.core.config import AppConfig
from sublingo.core.config import PROXY_MODE_CUSTOM
from sublingo.core.config import PROXY_MODE_DISABLED
from sublingo.core.models import DownloadResult
from sublingo.core.models import FontSubsetResult
from sublingo.core.models import MuxResult
from sublingo.core.models import TranslateResult
from sublingo.core.models import VideoInfo
from sublingo.core.workflow import run_workflow

pytestmark = pytest.mark.integration


def _video_info(title: str = "Demo Video") -> VideoInfo:
    return VideoInfo(
        url="https://example.com/v",
        video_id="abc123",
        title=title,
        duration=1,
        channel="c",
        upload_date="20260101",
        thumbnail_url="",
        view_count=1,
        available_subtitles={},
        available_auto_captions={},
    )


def _write_stage_files(project_dir: Path) -> tuple[Path, Path, Path, Path]:
    video = project_dir / "video.mp4"
    subtitle = project_dir / "video.sub-en.vtt"
    translated = project_dir / "video.sub-en.zh-Hans.ass"
    font = project_dir / "video.sub-en.zh-Hans.TestFont.ttf"
    video.write_text("v", encoding="utf-8")
    subtitle.write_text("WEBVTT\n", encoding="utf-8")
    translated.write_text("ass\n", encoding="utf-8")
    font.write_text("font\n", encoding="utf-8")
    return video, subtitle, translated, font


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("proxy_mode", "proxy", "expected_proxy"),
    [
        (PROXY_MODE_CUSTOM, "http://127.0.0.1:7890", "http://127.0.0.1:7890"),
        (PROXY_MODE_DISABLED, "http://127.0.0.1:7890", ""),
    ],
)
async def test_run_workflow_passes_proxy_to_extract_and_download(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    proxy_mode: str,
    proxy: str,
    expected_proxy: str,
) -> None:
    seen: dict[str, Any] = {"extract_proxy": None, "download_proxy": None}

    def fake_extract_info(*args: Any, **kwargs: Any) -> VideoInfo:
        seen["extract_proxy"] = kwargs.get("proxy")
        return _video_info()

    def fake_download(*args: Any, **kwargs: Any) -> DownloadResult:
        seen["download_proxy"] = kwargs.get("proxy")
        project_dir = kwargs["output_dir"]
        video, subtitle, _, _ = _write_stage_files(project_dir)
        return DownloadResult(
            success=True,
            video_path=video,
            subtitle_paths=[subtitle],
            video_title="Demo Video",
        )

    async def fake_translate(*args: Any, **kwargs: Any) -> TranslateResult:
        output_path = kwargs["output_dir"] / "video.sub-en.zh-Hans.ass"
        output_path.write_text("ass\n", encoding="utf-8")
        return TranslateResult(success=True, output_path=output_path)

    def fake_subset_font(*args: Any, **kwargs: Any) -> FontSubsetResult:
        output_path = kwargs["output_dir"] / "video.sub-en.zh-Hans.TestFont.ttf"
        output_path.write_text("font\n", encoding="utf-8")
        return FontSubsetResult(success=True, output_path=output_path)

    def fake_softsub(*args: Any, **kwargs: Any) -> MuxResult:
        output_path = kwargs["output_dir"] / "video.softsub.mkv"
        output_path.write_text("m\n", encoding="utf-8")
        return MuxResult(success=True, output_path=output_path)

    monkeypatch.setattr("sublingo.core.workflow.extract_info", fake_extract_info)
    monkeypatch.setattr("sublingo.core.workflow.download", fake_download)
    monkeypatch.setattr("sublingo.core.workflow.translate", fake_translate)
    monkeypatch.setattr("sublingo.core.workflow.subset_font", fake_subset_font)
    monkeypatch.setattr("sublingo.core.workflow.softsub", fake_softsub)

    config = AppConfig(
        target_language="zh-Hans",
        ai_api_key="token",
        font_file="TestFont.ttf",
        proxy_mode=proxy_mode,
        proxy=proxy,
    )
    font_dir = tmp_path / "fonts"
    font_dir.mkdir(parents=True, exist_ok=True)
    (font_dir / "TestFont.ttf").write_text("font\n", encoding="utf-8")

    result = await run_workflow(
        "https://example.com/v",
        config=config,
        cookie_file=tmp_path / "cookies.txt",
        font_dir=font_dir,
        output_dir=tmp_path / "output",
        progress=None,
    )

    assert result.success is True
    assert seen["extract_proxy"] == expected_proxy
    assert seen["download_proxy"] == expected_proxy


@pytest.mark.asyncio
async def test_run_workflow_uses_sanitized_project_dir_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observed_project_dir: Path | None = None

    def fake_extract_info(*args: Any, **kwargs: Any) -> VideoInfo:
        return _video_info(title="Demo:Video/Title*Unsafe?")

    def fake_download(*args: Any, **kwargs: Any) -> DownloadResult:
        nonlocal observed_project_dir
        project_dir = kwargs["output_dir"]
        observed_project_dir = project_dir
        video, subtitle, _, _ = _write_stage_files(project_dir)
        return DownloadResult(
            success=True,
            video_path=video,
            subtitle_paths=[subtitle],
            video_title="Demo Video",
        )

    async def fake_translate(*args: Any, **kwargs: Any) -> TranslateResult:
        output_path = kwargs["output_dir"] / "video.sub-en.zh-Hans.ass"
        output_path.write_text("ass\n", encoding="utf-8")
        return TranslateResult(success=True, output_path=output_path)

    def fake_subset_font(*args: Any, **kwargs: Any) -> FontSubsetResult:
        output_path = kwargs["output_dir"] / "video.sub-en.zh-Hans.TestFont.ttf"
        output_path.write_text("font\n", encoding="utf-8")
        return FontSubsetResult(success=True, output_path=output_path)

    def fake_softsub(*args: Any, **kwargs: Any) -> MuxResult:
        output_path = kwargs["output_dir"] / "video.softsub.mkv"
        output_path.write_text("m\n", encoding="utf-8")
        return MuxResult(success=True, output_path=output_path)

    monkeypatch.setattr("sublingo.core.workflow.extract_info", fake_extract_info)
    monkeypatch.setattr("sublingo.core.workflow.download", fake_download)
    monkeypatch.setattr("sublingo.core.workflow.translate", fake_translate)
    monkeypatch.setattr("sublingo.core.workflow.subset_font", fake_subset_font)
    monkeypatch.setattr("sublingo.core.workflow.softsub", fake_softsub)

    config = AppConfig(
        target_language="zh-Hans",
        ai_api_key="token",
        font_file="TestFont.ttf",
    )
    font_dir = tmp_path / "fonts"
    font_dir.mkdir(parents=True, exist_ok=True)
    (font_dir / "TestFont.ttf").write_text("font\n", encoding="utf-8")

    result = await run_workflow(
        "https://example.com/v",
        config=config,
        cookie_file=tmp_path / "cookies.txt",
        font_dir=font_dir,
        output_dir=tmp_path / "output",
        progress=None,
    )

    assert result.success is True
    assert observed_project_dir is not None
    assert observed_project_dir.name == "[abc123]Demo_Video_Title_Unsafe_"
