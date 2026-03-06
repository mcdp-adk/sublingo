from __future__ import annotations

from pathlib import Path

from sublingo.core.config import AppConfig
from sublingo.core.downloader import download, extract_info
from sublingo.core.ffmpeg import softsub
from sublingo.core.font import subset_font
from sublingo.core.models import ProgressCallback, ProjectStatus, WorkflowResult
from sublingo.core.transcript import generate_transcript
from sublingo.core.translator import translate

VIDEO_EXTENSIONS: set[str] = {".mp4", ".mkv", ".webm", ".mov", ".avi"}
SUBTITLE_EXTENSIONS: set[str] = {".vtt", ".srt"}
ASS_EXTENSION: str = ".ass"
TTF_EXTENSION: str = ".ttf"
SOFTSUB_SUFFIX: str = ".softsub.mkv"
SUBSET_SUFFIX: str = ".subset.ttf"
DEFAULT_TOTAL_STAGES: int = 5
STAGE_DOWNLOAD: str = "download"
STAGE_TRANSLATE: str = "translate"
STAGE_FONT: str = "font"
STAGE_MUX: str = "mux"
STAGE_TRANSCRIPT: str = "transcript"
STAGE_COMPLETE: str = "complete"
INVALID_PATH_CHARS: str = '<>:"/\\|?*'


def detect_project_status(project_dir: Path) -> ProjectStatus:
    return _detect_project_status(
        project_dir=project_dir,
        target_lang=AppConfig().target_language,
    )


async def run_workflow(
    url: str,
    *,
    config: AppConfig,
    cookie_file: Path,
    glossary_dir: Path | None = None,
    font_dir: Path | None = None,
    output_dir: Path,
    progress: ProgressCallback | None = None,
) -> WorkflowResult:
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        info = extract_info(url, cookie_file=cookie_file, proxy=config.proxy or None)
    except Exception as exc:  # noqa: BLE001
        return WorkflowResult(
            success=False,
            current_stage=STAGE_DOWNLOAD,
            error=f"Extract info failed: {exc}",
        )

    project_name = f"[{info.video_id}]{_sanitize_path_segment(info.title)}"
    project_dir = output_dir / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    return await _run_from_project(
        url=url,
        project_dir=project_dir,
        config=config,
        cookie_file=cookie_file,
        glossary_dir=glossary_dir,
        font_dir=font_dir,
        progress=progress,
        initial_title=info.title,
    )


async def resume_workflow(
    project_dir: Path,
    *,
    config: AppConfig,
    cookie_file: Path,
    glossary_dir: Path | None = None,
    font_dir: Path | None = None,
    output_dir: Path,
    progress: ProgressCallback | None = None,
) -> WorkflowResult:
    del output_dir

    status = _detect_project_status(
        project_dir=project_dir, target_lang=config.target_language
    )
    if status.next_stage == STAGE_DOWNLOAD:
        return WorkflowResult(
            success=False,
            current_stage=STAGE_DOWNLOAD,
            error="Cannot resume from download stage without URL",
        )

    return await _run_from_project(
        url=None,
        project_dir=project_dir,
        config=config,
        cookie_file=cookie_file,
        glossary_dir=glossary_dir,
        font_dir=font_dir,
        progress=progress,
        initial_title=project_dir.name,
    )


async def _run_from_project(
    *,
    url: str | None,
    project_dir: Path,
    config: AppConfig,
    cookie_file: Path,
    glossary_dir: Path | None,
    font_dir: Path | None,
    progress: ProgressCallback | None,
    initial_title: str,
) -> WorkflowResult:
    result = WorkflowResult(
        success=False,
        current_stage=STAGE_DOWNLOAD,
        video_title=initial_title,
    )
    project_dir.mkdir(parents=True, exist_ok=True)

    status = _detect_project_status(
        project_dir=project_dir, target_lang=config.target_language
    )

    result.current_stage = STAGE_DOWNLOAD
    _emit_stage(progress, stage=STAGE_DOWNLOAD, stage_status="active", stage_index=1)
    if not status.has_video or not status.has_subtitle:
        if not url:
            result.error = "Download prerequisites missing and URL is unavailable"
            return result
        result.download = download(
            url,
            output_dir=project_dir,
            cookie_file=cookie_file,
            proxy=config.proxy or None,
            progress=progress,
        )
        if result.download.video_title:
            result.video_title = result.download.video_title
        if not result.download.success:
            result.error = f"Download failed: {result.download.error}"
            return result
        status = _detect_project_status(
            project_dir=project_dir, target_lang=config.target_language
        )
    _emit_stage(progress, stage=STAGE_DOWNLOAD, stage_status="done", stage_index=1)

    subtitle_path = _find_subtitle_path(project_dir)
    video_path = _find_video_path(project_dir)
    translated_path = _find_translated_ass(project_dir, config.target_language)

    result.current_stage = STAGE_TRANSLATE
    _emit_stage(progress, stage=STAGE_TRANSLATE, stage_status="active", stage_index=2)
    if subtitle_path is not None and translated_path is None:
        glossary_path = _resolve_glossary_path(glossary_dir, config.target_language)
        result.translate = await translate(
            subtitle_path,
            target_lang=config.target_language,
            ai_config=config,
            glossary_path=glossary_path,
            output_dir=project_dir,
            progress=progress,
        )
        if not result.translate.success:
            result.error = f"Translate failed: {result.translate.error}"
            return result
        translated_path = result.translate.output_path
    _emit_stage(progress, stage=STAGE_TRANSLATE, stage_status="done", stage_index=2)

    result.current_stage = STAGE_FONT
    _emit_stage(progress, stage=STAGE_FONT, stage_status="active", stage_index=3)
    font_path = _find_subset_font_path(project_dir, config.font_file)
    if translated_path is not None and font_path is None:
        resolved_font = _resolve_font_file(config.font_file, font_dir)
        if resolved_font is None:
            result.error = f"Font file not found: {config.font_file}"
            return result
        result.font = subset_font(
            translated_path,
            resolved_font,
            output_dir=project_dir,
        )
        if not result.font.success:
            result.error = f"Font subset failed: {result.font.error}"
            return result
        font_path = result.font.output_path
    _emit_stage(progress, stage=STAGE_FONT, stage_status="done", stage_index=3)

    result.current_stage = STAGE_MUX
    _emit_stage(progress, stage=STAGE_MUX, stage_status="active", stage_index=4)
    has_final = _find_softsub_output(project_dir) is not None
    if (
        not has_final
        and video_path is not None
        and translated_path is not None
        and font_path is not None
    ):
        result.mux = softsub(
            video_path,
            translated_path,
            font_path=font_path,
            output_dir=project_dir,
            progress=progress,
        )
        if not result.mux.success:
            result.error = f"Mux failed: {result.mux.error}"
            return result
    _emit_stage(progress, stage=STAGE_MUX, stage_status="done", stage_index=4)

    result.current_stage = STAGE_TRANSCRIPT
    _emit_stage(progress, stage=STAGE_TRANSCRIPT, stage_status="active", stage_index=5)
    if config.generate_transcript and subtitle_path is not None:
        transcript_result = generate_transcript(subtitle_path, output_dir=project_dir)
        if not transcript_result.success and transcript_result.error:
            result.warnings.append(f"Transcript failed: {transcript_result.error}")
    _emit_stage(progress, stage=STAGE_TRANSCRIPT, stage_status="done", stage_index=5)

    result.current_stage = STAGE_COMPLETE
    result.success = True
    result.warnings.extend(_collect_stage_warnings(result))
    return result


def _detect_project_status(project_dir: Path, target_lang: str) -> ProjectStatus:
    status = ProjectStatus()
    status.has_video = _find_video_path(project_dir) is not None
    status.has_subtitle = _find_subtitle_path(project_dir) is not None
    status.has_translated = _find_translated_ass(project_dir, target_lang) is not None
    status.has_font = _find_any_font_artifact(project_dir) is not None
    status.has_final = _find_softsub_output(project_dir) is not None

    if not status.has_video or not status.has_subtitle:
        status.next_stage = STAGE_DOWNLOAD
    elif not status.has_translated:
        status.next_stage = STAGE_TRANSLATE
    elif not status.has_font:
        status.next_stage = STAGE_FONT
    elif not status.has_final:
        status.next_stage = STAGE_MUX
    else:
        status.next_stage = STAGE_COMPLETE

    return status


def _emit_stage(
    progress: ProgressCallback | None,
    *,
    stage: str,
    stage_status: str,
    stage_index: int,
) -> None:
    if progress is None:
        return
    progress.on_progress(
        stage_index,
        DEFAULT_TOTAL_STAGES,
        message=stage,
        stage=stage,
        stage_status=stage_status,
    )


def _collect_stage_warnings(result: WorkflowResult) -> list[str]:
    warnings: list[str] = []
    if result.download and result.download.warnings:
        warnings.extend(result.download.warnings)
    if result.translate and result.translate.warnings:
        warnings.extend(result.translate.warnings)
    if result.font and result.font.warnings:
        warnings.extend(result.font.warnings)
    if result.mux and result.mux.warnings:
        warnings.extend(result.mux.warnings)
    return warnings


def _sanitize_path_segment(value: str) -> str:
    cleaned = value
    for char in INVALID_PATH_CHARS:
        cleaned = cleaned.replace(char, "_")
    return cleaned.strip() or "video"


def _resolve_glossary_path(glossary_dir: Path | None, target_lang: str) -> Path | None:
    if glossary_dir is None:
        return None
    candidate = glossary_dir / f"{target_lang}.csv"
    if candidate.exists():
        return candidate
    return None


def _resolve_font_file(font_file: str, font_dir: Path | None) -> Path | None:
    direct = Path(font_file)
    if direct.is_absolute() and direct.exists():
        return direct

    if direct.exists():
        return direct

    if font_dir is None:
        return None

    in_dir = font_dir / font_file
    if in_dir.exists():
        return in_dir

    stem = Path(font_file).stem
    for ext in (".ttf", ".otf"):
        candidate = font_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def _find_video_path(project_dir: Path) -> Path | None:
    if not project_dir.exists():
        return None
    for path in sorted(project_dir.glob("*")):
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
            return path
    return None


def _find_subtitle_path(project_dir: Path) -> Path | None:
    if not project_dir.exists():
        return None
    for path in sorted(project_dir.glob("*")):
        if path.is_file() and path.suffix.lower() in SUBTITLE_EXTENSIONS:
            return path
    return None


def _find_translated_ass(project_dir: Path, target_lang: str) -> Path | None:
    if not project_dir.exists():
        return None
    lang_token = f".{target_lang}."
    for path in sorted(project_dir.glob(f"*{ASS_EXTENSION}")):
        if path.is_file() and lang_token in path.name:
            return path
    return None


def _find_subset_font_path(project_dir: Path, font_file: str) -> Path | None:
    if not project_dir.exists():
        return None

    font_stem = Path(font_file).stem
    for path in sorted(project_dir.glob(f"*{TTF_EXTENSION}")):
        if not path.is_file():
            continue
        if path.name.endswith(SUBSET_SUFFIX) or path.stem.endswith(f".{font_stem}"):
            return path
    return None


def _find_softsub_output(project_dir: Path) -> Path | None:
    if not project_dir.exists():
        return None
    for path in sorted(project_dir.glob(f"*{SOFTSUB_SUFFIX}")):
        if path.is_file():
            return path
    return None


def _find_any_font_artifact(project_dir: Path) -> Path | None:
    if not project_dir.exists():
        return None
    for path in sorted(project_dir.glob(f"*{TTF_EXTENSION}")):
        if not path.is_file():
            continue
        if path.name.endswith(SUBSET_SUFFIX) or "." in path.stem:
            return path
    return None
