from __future__ import annotations

import subprocess
from pathlib import Path

from sublingo.core.ffmpeg import hardsub, probe_streams, softsub
from sublingo.core.models import StreamInfo


def _completed_process(
    *, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["ffmpeg"],
        returncode=0,
        stdout=stdout,
        stderr=stderr,
    )


def test_probe_streams_parses_ffprobe_json(monkeypatch):
    payload = (
        '{"streams":[{"index":0,"codec_type":"video","codec_name":"h264"},'
        '{"index":1,"codec_type":"audio","codec_name":"aac",'
        '"tags":{"language":"eng","title":"Main Audio"}}]}'
    )

    def fake_run(*_args, **_kwargs):
        return _completed_process(stdout=payload)

    monkeypatch.setattr("sublingo.core.ffmpeg.subprocess.run", fake_run)

    streams = probe_streams(Path("/tmp/input.mp4"))

    assert streams == [
        StreamInfo(
            index=0, codec_type="video", codec_name="h264", language=None, title=None
        ),
        StreamInfo(
            index=1,
            codec_type="audio",
            codec_name="aac",
            language="eng",
            title="Main Audio",
        ),
    ]


def test_softsub_has_expected_map_order(monkeypatch, tmp_path: Path):
    video_path = tmp_path / "video.mp4"
    subtitle_path = tmp_path / "sub.ass"

    captured: dict[str, list[str]] = {}

    def fake_run(cmd, **_kwargs):
        captured["cmd"] = cmd
        return _completed_process()

    monkeypatch.setattr(
        "sublingo.core.ffmpeg.probe_streams",
        lambda _path: [
            StreamInfo(index=3, codec_type="subtitle", codec_name="subrip"),
            StreamInfo(index=5, codec_type="subtitle", codec_name="ass"),
        ],
    )
    monkeypatch.setattr("sublingo.core.ffmpeg.subprocess.run", fake_run)

    result = softsub(video_path, subtitle_path)

    assert result.success is True
    assert result.output_path == tmp_path / "video.softsub.mkv"

    maps: list[str] = []
    cmd = captured["cmd"]
    for index, token in enumerate(cmd):
        if token == "-map":
            maps.append(cmd[index + 1])
    assert maps == ["0:v", "0:a?", "1:s", "0:3", "0:5"]


def test_softsub_sets_disposition_for_new_and_existing_subtitles(
    monkeypatch, tmp_path: Path
):
    video_path = tmp_path / "movie.mp4"
    subtitle_path = tmp_path / "movie.ass"

    captured: dict[str, list[str]] = {}

    def fake_run(cmd, **_kwargs):
        captured["cmd"] = cmd
        return _completed_process()

    monkeypatch.setattr(
        "sublingo.core.ffmpeg.probe_streams",
        lambda _path: [
            StreamInfo(index=4, codec_type="subtitle", codec_name="ass"),
            StreamInfo(index=7, codec_type="subtitle", codec_name="subrip"),
        ],
    )
    monkeypatch.setattr("sublingo.core.ffmpeg.subprocess.run", fake_run)

    softsub(video_path, subtitle_path)
    cmd = captured["cmd"]

    assert "-disposition:s:0" in cmd
    assert cmd[cmd.index("-disposition:s:0") + 1] == "default"
    assert "-disposition:s:1" in cmd
    assert cmd[cmd.index("-disposition:s:1") + 1] == "0"
    assert "-disposition:s:2" in cmd
    assert cmd[cmd.index("-disposition:s:2") + 1] == "0"


def test_softsub_attaches_font_when_font_path_provided(monkeypatch, tmp_path: Path):
    video_path = tmp_path / "clip.mp4"
    subtitle_path = tmp_path / "clip.ass"
    font_path = tmp_path / "font.ttf"

    captured: dict[str, list[str]] = {}

    def fake_run(cmd, **_kwargs):
        captured["cmd"] = cmd
        return _completed_process()

    monkeypatch.setattr("sublingo.core.ffmpeg.probe_streams", lambda _path: [])
    monkeypatch.setattr("sublingo.core.ffmpeg.subprocess.run", fake_run)

    softsub(video_path, subtitle_path, font_path=font_path)
    cmd = captured["cmd"]

    assert "-attach" in cmd
    assert cmd[cmd.index("-attach") + 1] == str(font_path)
    assert "-metadata:s:t:0" in cmd
    assert cmd[cmd.index("-metadata:s:t:0") + 1] == "mimetype=font/ttf"


def test_hardsub_uses_ass_video_filter(monkeypatch, tmp_path: Path):
    video_path = tmp_path / "source.mp4"
    subtitle_path = tmp_path / "source.ass"

    captured: dict[str, list[str]] = {}

    def fake_run(cmd, **_kwargs):
        captured["cmd"] = cmd
        return _completed_process()

    monkeypatch.setattr("sublingo.core.ffmpeg.subprocess.run", fake_run)

    result = hardsub(video_path, subtitle_path)

    assert result.success is True
    assert result.output_path == tmp_path / "source.hardsub.mp4"
    cmd = captured["cmd"]
    assert "-vf" in cmd
    assert cmd[cmd.index("-vf") + 1] == f"ass={subtitle_path}"
