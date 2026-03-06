from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yt_dlp

from sublingo.core.models import DownloadResult, ProgressCallback, VideoInfo

YT_DLP_SUBTITLE_LANGS: list[str] = ["all", "-live_chat"]
YT_DLP_SUBTITLE_FORMAT: str = "srt/vtt/best"
YT_DLP_COMPAT_OPTIONS: set[str] = {"no-live-chat"}
YT_DLP_VIDEO_EXTENSIONS: set[str] = {".mp4", ".mkv", ".webm", ".mov", ".avi"}
YT_DLP_SUBTITLE_EXTENSIONS: set[str] = {".srt", ".vtt", ".ass"}
YT_DLP_OUTTMPL: str = "%(title)s.%(ext)s"


class YtDlpLogger:
    def __init__(self, progress: ProgressCallback | None) -> None:
        self._progress = progress

    def debug(self, msg: str) -> None:
        if self._progress is not None:
            self._progress.on_log("debug", msg)

    def warning(self, msg: str) -> None:
        if self._progress is not None:
            self._progress.on_log("warning", msg)

    def error(self, msg: str) -> None:
        if self._progress is not None:
            self._progress.on_log("error", msg)


def _map_video_info(info_dict: dict[str, Any]) -> VideoInfo:
    return VideoInfo(
        url=str(info_dict.get("webpage_url") or info_dict.get("original_url") or ""),
        video_id=str(info_dict.get("id") or ""),
        title=str(info_dict.get("title") or ""),
        duration=int(info_dict.get("duration") or 0),
        channel=str(info_dict.get("channel") or info_dict.get("uploader") or ""),
        upload_date=str(info_dict.get("upload_date") or ""),
        thumbnail_url=str(info_dict.get("thumbnail") or ""),
        view_count=int(info_dict.get("view_count") or 0),
        available_subtitles=dict(info_dict.get("subtitles") or {}),
        available_auto_captions=dict(info_dict.get("automatic_captions") or {}),
    )


def _build_common_ydl_opts(
    *,
    cookie_file: Path,
    proxy: str | None,
) -> dict[str, Any]:
    opts: dict[str, Any] = {
        "cookiefile": str(cookie_file),
        "extract_flat": False,
        "quiet": True,
        "no_warnings": False,
    }
    if proxy is not None:
        opts["proxy"] = proxy
    return opts


def extract_info(url: str, *, cookie_file: Path, proxy: str | None = None) -> VideoInfo:
    opts = _build_common_ydl_opts(cookie_file=cookie_file, proxy=proxy)
    with yt_dlp.YoutubeDL(cast(Any, opts)) as ydl:
        info_dict = cast(dict[str, Any], ydl.extract_info(url, download=False))

    if not isinstance(info_dict, dict):
        raise ValueError("yt-dlp did not return valid video metadata")
    return _map_video_info(info_dict)


def extract_playlist_info(
    url: str,
    *,
    cookie_file: Path,
    proxy: str | None = None,
) -> list[VideoInfo]:
    opts = _build_common_ydl_opts(cookie_file=cookie_file, proxy=proxy)
    with yt_dlp.YoutubeDL(cast(Any, opts)) as ydl:
        info_dict = cast(dict[str, Any], ydl.extract_info(url, download=False))

    if not isinstance(info_dict, dict):
        raise ValueError("yt-dlp did not return valid playlist metadata")

    entries = info_dict.get("entries")
    if entries is None:
        return [_map_video_info(info_dict)]

    results: list[VideoInfo] = []
    for entry in entries:
        if isinstance(entry, dict):
            results.append(_map_video_info(entry))
    return results


def _make_progress_hook(progress: ProgressCallback | None):
    if progress is None:
        return []

    def hook(data: dict[str, Any]) -> None:
        status = str(data.get("status") or "")
        if status == "downloading":
            total = int(
                data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            )
            downloaded = int(data.get("downloaded_bytes") or 0)
            progress.on_progress(
                downloaded,
                total,
                message=status,
                status=status,
                speed=data.get("speed"),
                eta=data.get("eta"),
                filename=data.get("filename"),
                downloaded_bytes=downloaded,
                total_bytes=total,
            )
        elif status == "finished":
            progress.on_progress(1, 1, message="finished", status=status)

    return [hook]


def _make_postprocessor_hook(progress: ProgressCallback | None):
    if progress is None:
        return []

    def hook(data: dict[str, Any]) -> None:
        progress.on_log(
            "info",
            "postprocessing",
            detail=(
                f"status={data.get('status')} "
                f"postprocessor={data.get('postprocessor')} "
                f"filepath={data.get('info_dict', {}).get('filepath')}"
            ),
        )

    return [hook]


def _extract_subtitle_paths_from_info(
    output_dir: Path, info_dict: dict[str, Any]
) -> list[Path]:
    subtitle_paths: list[Path] = []
    requested_subtitles = info_dict.get("requested_subtitles") or {}
    if isinstance(requested_subtitles, dict):
        for value in requested_subtitles.values():
            if not isinstance(value, dict):
                continue
            filepath = value.get("filepath")
            if filepath:
                subtitle_paths.append(Path(str(filepath)))

    if subtitle_paths:
        return subtitle_paths

    title = str(info_dict.get("title") or "")
    for path in output_dir.glob(f"{title}*.*"):
        if path.suffix.lower() not in YT_DLP_SUBTITLE_EXTENSIONS:
            continue
        subtitle_paths.append(path)
    return subtitle_paths


def _guess_language_from_subtitle_name(path: Path) -> str:
    suffixes = [segment for segment in path.stem.split(".") if segment]
    if len(suffixes) >= 2:
        return suffixes[-1]
    return "unknown"


def _rename_subtitle_files(
    output_dir: Path,
    *,
    title: str,
    subtitle_paths: list[Path],
) -> list[Path]:
    renamed: list[Path] = []
    for src in subtitle_paths:
        lang = _guess_language_from_subtitle_name(src)
        ext = src.suffix.lstrip(".")
        dest = output_dir / f"{title}.sub-{lang}.{ext}"
        if src == dest:
            renamed.append(src)
            continue
        src.rename(dest)
        renamed.append(dest)
    return renamed


def _find_video_path(output_dir: Path, title: str) -> Path | None:
    for path in sorted(output_dir.glob(f"{title}*")):
        if path.suffix.lower() in YT_DLP_VIDEO_EXTENSIONS and path.is_file():
            return path
    return None


def download(
    url: str,
    *,
    output_dir: Path,
    cookie_file: Path,
    proxy: str | None = None,
    progress: ProgressCallback | None = None,
) -> DownloadResult:
    output_dir.mkdir(parents=True, exist_ok=True)

    opts = _build_common_ydl_opts(cookie_file=cookie_file, proxy=proxy)
    opts.update(
        {
            "writesubtitles": True,
            "writeautomaticsub": False,
            "subtitleslangs": YT_DLP_SUBTITLE_LANGS,
            "subtitlesformat": YT_DLP_SUBTITLE_FORMAT,
            "restrictfilenames": True,
            "outtmpl": str(output_dir / YT_DLP_OUTTMPL),
            "compat_options": YT_DLP_COMPAT_OPTIONS,
            "progress_hooks": _make_progress_hook(progress),
            "postprocessor_hooks": _make_postprocessor_hook(progress),
            "logger": YtDlpLogger(progress),
        }
    )

    try:
        with yt_dlp.YoutubeDL(cast(Any, opts)) as ydl:
            info_dict = cast(dict[str, Any], ydl.extract_info(url, download=True))

        if not isinstance(info_dict, dict):
            return DownloadResult(
                success=False, error="yt-dlp did not return valid data"
            )

        title = str(info_dict.get("title") or "video")
        subtitle_paths = _extract_subtitle_paths_from_info(output_dir, info_dict)
        warnings: list[str] = []

        if not subtitle_paths:
            warn = "No manual subtitles found for this video"
            warnings.append(warn)
            if progress is not None:
                progress.on_log("warning", warn)
        else:
            subtitle_paths = _rename_subtitle_files(
                output_dir,
                title=title,
                subtitle_paths=subtitle_paths,
            )

        video_path = _find_video_path(output_dir, title)

        return DownloadResult(
            success=True,
            video_path=video_path,
            subtitle_paths=subtitle_paths,
            video_title=title,
            warnings=warnings,
        )
    except Exception as exc:  # noqa: BLE001
        if progress is not None:
            progress.on_log("error", str(exc))
        return DownloadResult(success=False, error=str(exc))
