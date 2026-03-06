from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sublingo.core.downloader import download, extract_info


class ProgressSpy:
    def __init__(self) -> None:
        self.progress_events: list[tuple[int, int, str, dict[str, Any]]] = []
        self.logs: list[tuple[str, str, str]] = []

    def on_progress(
        self,
        current: int,
        total: int,
        message: str = "",
        **meta: Any,
    ) -> None:
        self.progress_events.append((current, total, message, meta))

    def on_log(self, level: str, message: str, detail: str = "") -> None:
        self.logs.append((level, message, detail))


class FakeYoutubeDL:
    created_opts: list[dict[str, Any]] = []
    next_info: dict[str, Any] | None = None
    next_error: Exception | None = None

    def __init__(self, opts: dict[str, Any]) -> None:
        self.opts = opts
        FakeYoutubeDL.created_opts.append(opts)

    def __enter__(self) -> FakeYoutubeDL:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def extract_info(self, url: str, download: bool = False) -> dict[str, Any]:
        if FakeYoutubeDL.next_error is not None:
            raise FakeYoutubeDL.next_error
        assert isinstance(url, str)
        assert isinstance(download, bool)
        if FakeYoutubeDL.next_info is None:
            raise RuntimeError("FakeYoutubeDL.next_info is not set")
        return FakeYoutubeDL.next_info


@pytest.fixture(autouse=True)
def reset_fake_state() -> None:
    FakeYoutubeDL.created_opts = []
    FakeYoutubeDL.next_info = None
    FakeYoutubeDL.next_error = None


def test_extract_info_constructs_params_with_cookie_and_proxy(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("sublingo.core.downloader.yt_dlp.YoutubeDL", FakeYoutubeDL)
    FakeYoutubeDL.next_info = {
        "webpage_url": "https://example.com/watch?v=abc",
        "id": "abc",
        "title": "Video Title",
        "duration": 10,
        "channel": "Channel",
        "upload_date": "20260101",
        "thumbnail": "https://example.com/thumb.jpg",
        "view_count": 100,
        "subtitles": {"en": [{"ext": "srt"}]},
        "automatic_captions": {},
    }

    info = extract_info(
        "https://example.com/watch?v=abc",
        cookie_file=Path("/tmp/cookies.txt"),
        proxy="http://127.0.0.1:8080",
    )

    opts = FakeYoutubeDL.created_opts[-1]
    assert opts["cookiefile"] == "/tmp/cookies.txt"
    assert opts["proxy"] == "http://127.0.0.1:8080"
    assert opts["extract_flat"] is False
    assert info.video_id == "abc"
    assert info.title == "Video Title"


def test_download_constructs_expected_yt_dlp_params(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr("sublingo.core.downloader.yt_dlp.YoutubeDL", FakeYoutubeDL)
    title = "SampleVideo"
    video_file = tmp_path / f"{title}.mp4"
    subtitle_file = tmp_path / f"{title}.en.srt"
    video_file.write_text("video", encoding="utf-8")
    subtitle_file.write_text("sub", encoding="utf-8")

    FakeYoutubeDL.next_info = {
        "title": title,
        "requested_subtitles": {
            "en": {"filepath": str(subtitle_file)},
        },
    }

    result = download(
        "https://example.com/watch?v=abc",
        output_dir=tmp_path,
        cookie_file=Path("/tmp/cookies.txt"),
        proxy="socks5://127.0.0.1:1080",
    )

    opts = FakeYoutubeDL.created_opts[-1]
    assert opts["cookiefile"] == "/tmp/cookies.txt"
    assert opts["proxy"] == "socks5://127.0.0.1:1080"
    assert opts["writesubtitles"] is True
    assert opts["writeautomaticsub"] is False
    assert opts["subtitleslangs"] == ["all", "-live_chat"]
    assert opts["subtitlesformat"] == "srt/vtt/best"
    assert opts["restrictfilenames"] is True
    assert opts["quiet"] is True
    assert opts["no_warnings"] is False
    assert result.success is True


def test_extract_info_sets_empty_proxy_to_disable_env_proxy(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("sublingo.core.downloader.yt_dlp.YoutubeDL", FakeYoutubeDL)
    FakeYoutubeDL.next_info = {
        "webpage_url": "https://example.com/watch?v=abc",
        "id": "abc",
        "title": "Video Title",
        "duration": 10,
        "channel": "Channel",
        "upload_date": "20260101",
        "thumbnail": "https://example.com/thumb.jpg",
        "view_count": 100,
        "subtitles": {},
        "automatic_captions": {},
    }

    extract_info(
        "https://example.com/watch?v=abc",
        cookie_file=Path("/tmp/cookies.txt"),
        proxy="",
    )

    opts = FakeYoutubeDL.created_opts[-1]
    assert opts["proxy"] == ""


def test_progress_hook_maps_yt_dlp_payload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr("sublingo.core.downloader.yt_dlp.YoutubeDL", FakeYoutubeDL)
    spy = ProgressSpy()

    title = "HookVideo"
    video_file = tmp_path / f"{title}.mp4"
    video_file.write_text("video", encoding="utf-8")
    FakeYoutubeDL.next_info = {
        "title": title,
        "requested_subtitles": {},
    }

    download(
        "https://example.com/watch?v=abc",
        output_dir=tmp_path,
        cookie_file=Path("/tmp/cookies.txt"),
        progress=spy,
    )

    opts = FakeYoutubeDL.created_opts[-1]
    hook = opts["progress_hooks"][0]
    hook(
        {
            "status": "downloading",
            "downloaded_bytes": 512,
            "total_bytes": 1024,
            "speed": 2048,
            "eta": 1,
            "filename": "a.mp4",
        }
    )

    current, total, message, meta = spy.progress_events[-1]
    assert current == 512
    assert total == 1024
    assert message == "downloading"
    assert meta["speed"] == 2048
    assert meta["eta"] == 1
    assert meta["filename"] == "a.mp4"


def test_download_renames_subtitle_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr("sublingo.core.downloader.yt_dlp.YoutubeDL", FakeYoutubeDL)

    title = "RenameVideo"
    video_file = tmp_path / f"{title}.mp4"
    old_subtitle = tmp_path / f"{title}.en.vtt"
    video_file.write_text("video", encoding="utf-8")
    old_subtitle.write_text("WEBVTT", encoding="utf-8")

    FakeYoutubeDL.next_info = {
        "title": title,
        "requested_subtitles": {
            "en": {"filepath": str(old_subtitle)},
        },
    }

    result = download(
        "https://example.com/watch?v=abc",
        output_dir=tmp_path,
        cookie_file=Path("/tmp/cookies.txt"),
    )

    new_subtitle = tmp_path / f"{title}.sub-en.vtt"
    assert result.success is True
    assert old_subtitle.exists() is False
    assert new_subtitle.exists() is True
    assert result.subtitle_paths == [new_subtitle]


def test_download_logs_warning_when_no_subtitles(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setattr("sublingo.core.downloader.yt_dlp.YoutubeDL", FakeYoutubeDL)
    spy = ProgressSpy()

    title = "NoSubtitle"
    (tmp_path / f"{title}.mp4").write_text("video", encoding="utf-8")
    FakeYoutubeDL.next_info = {
        "title": title,
        "requested_subtitles": {},
    }

    result = download(
        "https://example.com/watch?v=abc",
        output_dir=tmp_path,
        cookie_file=Path("/tmp/cookies.txt"),
        progress=spy,
    )

    assert result.success is True
    assert "No manual subtitles found" in result.warnings[0]
    assert ("warning", result.warnings[0], "") in spy.logs


def test_download_handles_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr("sublingo.core.downloader.yt_dlp.YoutubeDL", FakeYoutubeDL)
    FakeYoutubeDL.next_error = RuntimeError("boom")

    result = download(
        "https://example.com/watch?v=abc",
        output_dir=tmp_path,
        cookie_file=Path("/tmp/cookies.txt"),
    )

    assert result.success is False
    assert result.error == "boom"
