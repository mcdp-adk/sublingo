from __future__ import annotations

import json
import importlib
import subprocess
from pathlib import Path

from sublingo.core.constants import (
    FFMPEG_ERROR_TRUNCATE_LENGTH,
    FFMPEG_FFMPEG_TIMEOUT_S,
    FFMPEG_FFPROBE_TIMEOUT_S,
)
from sublingo.core.models import BurnResult, MuxResult, ProgressCallback, StreamInfo

FFPROBE_COMMAND = "ffprobe"
FFMPEG_COMMAND = "ffmpeg"
UTF8_CHARSET = "UTF-8"
SOFTSUB_SUFFIX = ".softsub.mkv"
HARDSUB_SUFFIX = ".hardsub.mp4"
ATTACHMENT_MIMETYPE = "mimetype=font/ttf"
ASS_FILTER_PREFIX = "ass="
VIDEO_CODEC_COPY = "copy"
AUDIO_CODEC_COPY = "copy"
HARDSUB_VIDEO_CODEC = "libx264"
SUBTITLE_CODEC_ASS = "ass"
SUBTITLE_CODEC_COPY = "copy"

_STATIC_FFMPEG = importlib.import_module("static_ffmpeg")
_STATIC_FFMPEG.add_paths()


def probe_streams(video_path: Path) -> list[StreamInfo]:
    try:
        result = subprocess.run(
            [
                FFPROBE_COMMAND,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=FFMPEG_FFPROBE_TIMEOUT_S,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0:
        return []

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    streams: list[StreamInfo] = []
    for stream in payload.get("streams", []):
        tags = stream.get("tags", {})
        streams.append(
            StreamInfo(
                index=int(stream.get("index", 0)),
                codec_type=str(stream.get("codec_type", "unknown")),
                codec_name=str(stream.get("codec_name", "unknown")),
                language=tags.get("language"),
                title=tags.get("title"),
            )
        )
    return streams


def softsub(
    video_path: Path,
    subtitle_path: Path,
    *,
    font_path: Path | None = None,
    output_dir: Path | None = None,
    progress: ProgressCallback | None = None,
) -> MuxResult:
    out_dir = output_dir or video_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{video_path.stem}{SOFTSUB_SUFFIX}"

    existing_subtitles = [
        s for s in probe_streams(video_path) if s.codec_type == "subtitle"
    ]

    args: list[str] = [
        "-i",
        str(video_path),
        "-sub_charenc",
        UTF8_CHARSET,
        "-i",
        str(subtitle_path),
        "-map",
        "0:v",
        "-map",
        "0:a?",
        "-map",
        "1:s",
    ]

    if font_path is not None:
        args.extend(["-attach", str(font_path), "-metadata:s:t:0", ATTACHMENT_MIMETYPE])

    args.extend(
        [
            "-c:s:0",
            SUBTITLE_CODEC_ASS,
            "-disposition:s:0",
            "default",
        ]
    )

    for subtitle_index, stream in enumerate(existing_subtitles, start=1):
        args.extend(
            [
                "-map",
                f"0:{stream.index}",
                f"-c:s:{subtitle_index}",
                SUBTITLE_CODEC_COPY,
                f"-disposition:s:{subtitle_index}",
                "0",
            ]
        )

    args.extend(
        [
            "-c:v",
            VIDEO_CODEC_COPY,
            "-c:a",
            AUDIO_CODEC_COPY,
            "-y",
            str(output_path),
        ]
    )

    if progress:
        progress.on_log("info", f"Running ffmpeg softsub for: {video_path.name}")

    try:
        result = _run_ffmpeg(args, progress=progress, timeout=FFMPEG_FFMPEG_TIMEOUT_S)
    except FileNotFoundError:
        return MuxResult(success=False, error="ffmpeg not found on PATH")
    except subprocess.TimeoutExpired:
        return MuxResult(success=False, error="ffmpeg timed out")

    if result.returncode != 0:
        return MuxResult(success=False, error=_build_ffmpeg_error(result))
    return MuxResult(success=True, output_path=output_path)


def hardsub(
    video_path: Path,
    subtitle_path: Path,
    *,
    font_path: Path | None = None,
    output_dir: Path | None = None,
    progress: ProgressCallback | None = None,
) -> BurnResult:
    del font_path

    out_dir = output_dir or video_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{video_path.stem}{HARDSUB_SUFFIX}"

    args: list[str] = [
        "-i",
        str(video_path),
        "-vf",
        f"{ASS_FILTER_PREFIX}{subtitle_path}",
        "-c:v",
        HARDSUB_VIDEO_CODEC,
        "-c:a",
        AUDIO_CODEC_COPY,
        "-y",
        str(output_path),
    ]

    if progress:
        progress.on_log("info", f"Running ffmpeg hardsub for: {video_path.name}")

    try:
        result = _run_ffmpeg(args, progress=progress, timeout=FFMPEG_FFMPEG_TIMEOUT_S)
    except FileNotFoundError:
        return BurnResult(success=False, error="ffmpeg not found on PATH")
    except subprocess.TimeoutExpired:
        return BurnResult(success=False, error="ffmpeg timed out")

    if result.returncode != 0:
        return BurnResult(success=False, error=_build_ffmpeg_error(result))
    return BurnResult(success=True, output_path=output_path)


def _run_ffmpeg(
    args: list[str],
    *,
    progress: ProgressCallback | None = None,
    timeout: int,
) -> subprocess.CompletedProcess:
    if progress:
        progress.on_progress(1, 1, "Running ffmpeg")
    return subprocess.run(
        [FFMPEG_COMMAND, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _build_ffmpeg_error(result: subprocess.CompletedProcess) -> str:
    stderr = result.stderr.strip()
    if len(stderr) > FFMPEG_ERROR_TRUNCATE_LENGTH:
        short_err = stderr[:FFMPEG_ERROR_TRUNCATE_LENGTH] + "..."
    else:
        short_err = stderr
    return f"ffmpeg failed (exit {result.returncode}): {short_err}"
