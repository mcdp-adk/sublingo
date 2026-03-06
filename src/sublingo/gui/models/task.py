from __future__ import annotations

import asyncio
import inspect
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from sublingo.core.config import AppConfig
from sublingo.core.config import ConfigManager
from sublingo.core.downloader import download
from sublingo.core.ffmpeg import hardsub, softsub
from sublingo.core.font import subset_font
from sublingo.core.models import ProgressCallback
from sublingo.core.transcript import generate_transcript
from sublingo.core.translator import translate
from sublingo.core.workflow import run_workflow

TASK_PERSISTENCE_FILENAME: str = "tasks.json"
GLOSSARIES_DIRNAME: str = "glossaries"
FONTS_DIRNAME: str = "fonts"
DEFAULT_FAILURE_MESSAGE: str = "任务失败"
DEFAULT_WORKER_ERROR_MESSAGE: str = "无法创建任务 worker"
STAGE_PENDING: str = "pending"
STAGE_ACTIVE: str = "active"
STAGE_DONE: str = "done"
STAGE_ERROR: str = "error"
MILLISECONDS_PER_SECOND: int = 1000


class TaskType(Enum):
    WORKFLOW = "workflow"
    DOWNLOAD = "download"
    TRANSLATE = "translate"
    SOFTSUB = "softsub"
    HARDSUB = "hardsub"
    TRANSCRIPT = "transcript"
    FONT_SUBSET = "font_subset"


class TaskStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


TASK_TYPE_DISPLAY: dict[TaskType, str] = {
    TaskType.WORKFLOW: "完整工作流",
    TaskType.DOWNLOAD: "仅下载",
    TaskType.TRANSLATE: "仅翻译",
    TaskType.SOFTSUB: "仅软字幕",
    TaskType.HARDSUB: "仅硬字幕",
    TaskType.TRANSCRIPT: "仅转录",
    TaskType.FONT_SUBSET: "仅字体子集化",
}


TASK_STAGES: dict[TaskType, list[str]] = {
    TaskType.WORKFLOW: ["下载", "翻译", "字体子集", "软字幕", "转录"],
    TaskType.DOWNLOAD: ["下载"],
    TaskType.TRANSLATE: ["分段", "翻译", "校对"],
    TaskType.SOFTSUB: ["软字幕"],
    TaskType.HARDSUB: ["硬字幕"],
    TaskType.TRANSCRIPT: ["转录"],
    TaskType.FONT_SUBSET: ["字体子集"],
}

_DEFAULT_STAGE_BY_TASK: dict[TaskType, str] = {
    TaskType.DOWNLOAD: "download",
    TaskType.SOFTSUB: "softsub",
    TaskType.HARDSUB: "hardsub",
    TaskType.TRANSCRIPT: "transcript",
    TaskType.FONT_SUBSET: "font_subset",
}

_BACKEND_STAGE_TO_DISPLAY: dict[str, str] = {
    "download": "下载",
    "downloading": "下载",
    "finished": "下载",
    "segment": "分段",
    "segmenting": "分段",
    "translate": "翻译",
    "translating": "翻译",
    "proofread": "校对",
    "proofreading": "校对",
    "font": "字体子集",
    "font_subset": "字体子集",
    "softsub": "软字幕",
    "mux": "软字幕",
    "hardsub": "硬字幕",
    "burn": "硬字幕",
    "transcript": "转录",
    "complete": "完成",
}


def _normalize_path_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Path):
        return str(value)
    return ""


def _describe_task(task: "TaskInfo") -> str:
    for key in ("url", "subtitle_file", "video_file", "font_file"):
        value = _normalize_path_text(task.params.get(key))
        if not value:
            continue
        if key == "url":
            return value
        return Path(value).name
    return ""


@dataclass
class TaskInfo:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    task_type: TaskType = TaskType.WORKFLOW
    params: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.QUEUED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stages: list[str] = field(default_factory=list)
    stage_statuses: dict[str, str] = field(default_factory=dict)
    current_stage: str = ""
    progress_percent: int = 0
    progress_message: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str | None = None
    video_title: str = ""

    def __post_init__(self) -> None:
        if not self.stages:
            self.stages = list(TASK_STAGES.get(self.task_type, []))

        normalized_statuses = {
            stage: self.stage_statuses.get(stage, STAGE_PENDING)
            for stage in self.stages
        }
        self.stage_statuses = normalized_statuses

        if self.current_stage and self.current_stage not in self.stage_statuses:
            self.current_stage = ""

    @property
    def display_name(self) -> str:
        task_name = TASK_TYPE_DISPLAY.get(self.task_type, "任务")
        suffix = self.video_title or _describe_task(self)
        if not suffix:
            return task_name
        return f"{task_name}  {suffix}"

    @property
    def status_summary(self) -> str:
        if self.status == TaskStatus.COMPLETED:
            return "完成"
        if self.status == TaskStatus.FAILED:
            return "失败"
        if self.status == TaskStatus.RUNNING and self.current_stage:
            if self.progress_percent > 0:
                return f"{self.current_stage} {self.progress_percent}%"
            return self.current_stage
        return "排队中"

    def mark_running(self) -> None:
        self.status = TaskStatus.RUNNING
        self.error = None
        if self.stages and not self.current_stage:
            self.current_stage = self.stages[0]
        if self.current_stage in self.stage_statuses:
            self.stage_statuses[self.current_stage] = STAGE_ACTIVE

    def update_progress(
        self,
        *,
        current: int,
        total: int,
        message: str,
        meta: dict[str, Any],
        stage_name: str | None,
    ) -> None:
        self.progress_message = message
        self.meta = dict(meta)

        if stage_name and stage_name in self.stage_statuses:
            self._activate_stage(stage_name)
            stage_status = str(meta.get("stage_status") or "")
            if stage_status == STAGE_DONE:
                self.stage_statuses[stage_name] = STAGE_DONE

        active_stage = stage_name or self.current_stage
        if total > 0 and active_stage in self.stages:
            stage_index = self.stages.index(active_stage)
            stage_width = 100 / max(len(self.stages), 1)
            base_progress = int(stage_index * stage_width)
            stage_progress = int((current / total) * stage_width)
            self.progress_percent = min(base_progress + stage_progress, 99)

    def mark_completed(self, result: Any = None) -> None:
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.error = None
        self.progress_percent = 100
        if self.stages:
            self.current_stage = self.stages[-1]
        for stage in self.stages:
            self.stage_statuses[stage] = STAGE_DONE

    def mark_failed(
        self, error: str, *, failed_stage: str | None = None, result: Any = None
    ) -> None:
        self.status = TaskStatus.FAILED
        self.error = error
        self.result = result
        self.progress_message = error

        if failed_stage and failed_stage in self.stage_statuses:
            self.current_stage = failed_stage
            self.stage_statuses[failed_stage] = STAGE_ERROR
        elif self.current_stage in self.stage_statuses:
            self.stage_statuses[self.current_stage] = STAGE_ERROR

    def _activate_stage(self, stage_name: str) -> None:
        self.current_stage = stage_name
        for stage in self.stages:
            if stage == stage_name:
                break
            if self.stage_statuses[stage] != STAGE_DONE:
                self.stage_statuses[stage] = STAGE_DONE
        self.stage_statuses[stage_name] = STAGE_ACTIVE


class _WorkerProgressCallback:
    def __init__(
        self,
        progress_signal: Any,
        log_signal: Any,
    ) -> None:
        self._progress_signal = progress_signal
        self._log_signal = log_signal

    def on_progress(
        self, current: int, total: int, message: str = "", **meta: Any
    ) -> None:
        self._progress_signal.emit(current, total, message, dict(meta))

    def on_log(self, level: str, message: str, detail: str = "") -> None:
        self._log_signal.emit(level, message, detail)


class _TaskWorker(QThread):
    progress = Signal(int, int, str, dict)
    log = Signal(str, str, str)
    result_ready = Signal(object)
    task_error = Signal(object)

    def __init__(
        self,
        runner: Callable[[ProgressCallback | None], Any],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._runner = runner

    def run(self) -> None:
        callback = _WorkerProgressCallback(self.progress, self.log)
        try:
            outcome = self._runner(callback)
            if inspect.isawaitable(outcome):
                outcome = asyncio.run(self._await_outcome(outcome))
        except Exception as exc:  # noqa: BLE001
            self.task_error.emit(exc)
            return

        self.result_ready.emit(outcome)

    async def _await_outcome(self, outcome: Any) -> Any:
        return await outcome


class TaskManager(QObject):
    task_created = Signal(str)
    task_started = Signal(str)
    task_progress = Signal(str, int, int, str, dict)
    task_log = Signal(str, str, str, str)
    task_finished = Signal(str)
    task_failed = Signal(str, str)

    def __init__(
        self,
        config_mgr: ConfigManager,
        parent: QObject | None = None,
        persistence_path: Path | None = None,
    ) -> None:
        super().__init__(parent)
        self._config_mgr = config_mgr
        self._persistence_path = (
            persistence_path or config_mgr.project_root / TASK_PERSISTENCE_FILENAME
        )
        self._tasks = self._load_tasks()
        self._order = list(self._tasks)
        self._current_worker: _TaskWorker | QObject | None = None
        self._current_task_id: str | None = None
        self._next_task_timer: QTimer | None = None

    @property
    def tasks(self) -> dict[str, TaskInfo]:
        return self._tasks

    @property
    def task_order(self) -> list[str]:
        return list(self._order)

    def get_task(self, task_id: str) -> TaskInfo | None:
        return self._tasks.get(task_id)

    def create_task(self, task_type: TaskType, params: dict[str, Any]) -> str:
        task = TaskInfo(task_type=task_type, params=dict(params))
        self._tasks[task.id] = task
        self._order.append(task.id)
        self._persist_tasks()
        self.task_created.emit(task.id)
        self._try_run_next()
        return task.id

    def _try_run_next(self) -> None:
        if self._current_worker is not None:
            return

        for task_id in self._order:
            task = self._tasks.get(task_id)
            if task is None:
                continue
            if task.status == TaskStatus.QUEUED:
                self._run_task(task_id)
                return

    def _run_task(self, task_id: str) -> None:
        task = self._tasks[task_id]
        worker = self._create_worker(task)
        if worker is None:
            task.mark_failed(DEFAULT_WORKER_ERROR_MESSAGE)
            self._persist_tasks()
            self.task_failed.emit(task_id, task.error or DEFAULT_WORKER_ERROR_MESSAGE)
            self._schedule_next_task()
            return

        task.mark_running()
        self._current_worker = worker
        self._current_task_id = task_id
        self._persist_tasks()
        self.task_started.emit(task_id)

        worker.progress.connect(
            lambda current, total, message, meta: self._on_progress(
                task_id, current, total, message, meta
            )
        )
        worker.log.connect(
            lambda level, message, detail: self._on_log(task_id, level, message, detail)
        )
        worker.result_ready.connect(lambda result: self._on_finished(task_id, result))
        worker.task_error.connect(lambda exc: self._on_error(task_id, exc))
        worker.start()

    def _create_worker(self, task: TaskInfo) -> _TaskWorker | None:
        runner = self._build_runner(task)
        if runner is None:
            return None
        return _TaskWorker(runner, self)

    def _build_runner(
        self, task: TaskInfo
    ) -> Callable[[ProgressCallback | None], Any] | None:
        task_config = self._build_task_config(task)
        cookie_file = self._config_mgr.cookie_file
        output_dir = self._resolve_output_dir(task.params)
        glossary_dir = self._resolve_glossary_dir()
        glossary_path = self._resolve_glossary_path(task_config.target_language)

        if task.task_type == TaskType.WORKFLOW:
            url = str(task.params["url"])
            return lambda progress: run_workflow(
                url,
                config=task_config,
                cookie_file=cookie_file,
                glossary_dir=glossary_dir,
                font_dir=self._resolve_font_dir(),
                output_dir=output_dir,
                progress=progress,
            )

        if task.task_type == TaskType.DOWNLOAD:
            url = str(task.params["url"])
            return lambda progress: download(
                url,
                output_dir=output_dir,
                cookie_file=cookie_file,
                proxy=task_config.proxy or None,
                progress=progress,
            )

        if task.task_type == TaskType.TRANSLATE:
            subtitle_path = Path(str(task.params["subtitle_file"]))
            return lambda progress: translate(
                subtitle_path,
                target_lang=task_config.target_language,
                ai_config=task_config,
                glossary_path=glossary_path,
                output_dir=output_dir,
                progress=progress,
            )

        if task.task_type == TaskType.SOFTSUB:
            video_path = Path(str(task.params["video_file"]))
            subtitle_path = Path(str(task.params["subtitle_file"]))
            font_path = self._resolve_font_path(
                task.params.get("font_file"), task_config
            )
            return lambda progress: softsub(
                video_path,
                subtitle_path,
                font_path=font_path,
                output_dir=output_dir,
                progress=progress,
            )

        if task.task_type == TaskType.HARDSUB:
            video_path = Path(str(task.params["video_file"]))
            subtitle_path = Path(str(task.params["subtitle_file"]))
            font_path = self._resolve_font_path(
                task.params.get("font_file"), task_config
            )
            return lambda progress: hardsub(
                video_path,
                subtitle_path,
                font_path=font_path,
                output_dir=output_dir,
                progress=progress,
            )

        if task.task_type == TaskType.TRANSCRIPT:
            subtitle_path = Path(str(task.params["subtitle_file"]))
            return lambda _progress: generate_transcript(
                subtitle_path,
                output_dir=output_dir,
            )

        if task.task_type == TaskType.FONT_SUBSET:
            subtitle_path = Path(str(task.params["subtitle_file"]))
            font_path = self._resolve_font_path(
                task.params.get("font_file"), task_config
            )
            if font_path is None:
                return None
            return lambda _progress: subset_font(
                subtitle_path,
                font_path,
                output_dir=output_dir,
            )

        return None

    def _on_progress(
        self, task_id: str, current: int, total: int, message: str, meta: dict[str, Any]
    ) -> None:
        task = self._tasks.get(task_id)
        if task is None:
            return

        stage_name = self._map_stage_name(
            task,
            backend_stage=str(meta.get("stage") or ""),
            message=message,
        )
        task.update_progress(
            current=current,
            total=total,
            message=message,
            meta=meta,
            stage_name=stage_name,
        )
        self._persist_tasks()
        self.task_progress.emit(task_id, current, total, message, meta)

    def _on_log(self, task_id: str, level: str, message: str, detail: str) -> None:
        self.task_log.emit(task_id, level, message, detail)

    def _on_finished(self, task_id: str, result: object) -> None:
        task = self._tasks.get(task_id)
        if task is None:
            self._cleanup_worker()
            return

        task.result = result
        video_title = getattr(result, "video_title", "")
        if video_title:
            task.video_title = video_title

        if getattr(result, "success", True):
            task.mark_completed(result)
            self._persist_tasks()
            self.task_finished.emit(task_id)
        else:
            failed_stage = self._map_stage_name(
                task,
                backend_stage=str(getattr(result, "current_stage", "") or ""),
                message=task.progress_message,
            )
            error_message = getattr(result, "error", None) or DEFAULT_FAILURE_MESSAGE
            task.mark_failed(error_message, failed_stage=failed_stage, result=result)
            self._persist_tasks()
            self.task_failed.emit(task_id, error_message)

        self._cleanup_worker()
        self._schedule_next_task()

    def _on_error(self, task_id: str, exc: object) -> None:
        task = self._tasks.get(task_id)
        if task is None:
            self._cleanup_worker()
            return

        failed_stage = self._map_stage_name(
            task,
            backend_stage=_DEFAULT_STAGE_BY_TASK.get(task.task_type, ""),
            message=task.progress_message,
        )
        error_message = str(exc)
        task.mark_failed(error_message, failed_stage=failed_stage)
        self._persist_tasks()
        self.task_failed.emit(task_id, error_message)
        self._cleanup_worker()
        self._schedule_next_task()

    def _schedule_next_task(self) -> None:
        delay_seconds = int(max(self._config_mgr.config.batch_delay_seconds, 0))
        if delay_seconds == 0:
            self._try_run_next()
            return

        if self._next_task_timer is not None and self._next_task_timer.isActive():
            self._next_task_timer.stop()
            self._next_task_timer.deleteLater()

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(self._on_next_task_timer_timeout)
        timer.start(delay_seconds * MILLISECONDS_PER_SECOND)
        self._next_task_timer = timer

    def _on_next_task_timer_timeout(self) -> None:
        timer = self._next_task_timer
        self._next_task_timer = None
        if timer is not None:
            timer.deleteLater()
        self._try_run_next()

    def _map_stage_name(
        self, task: TaskInfo, *, backend_stage: str, message: str
    ) -> str | None:
        candidate = backend_stage or _DEFAULT_STAGE_BY_TASK.get(task.task_type, "")
        stage_name = _BACKEND_STAGE_TO_DISPLAY.get(candidate)

        message_lower = message.lower()
        if stage_name is None and "proofread" in message_lower:
            stage_name = "校对"
        if stage_name is None and "translat" in message_lower:
            stage_name = "翻译"
        if stage_name is None and "download" in message_lower:
            stage_name = "下载"
        if stage_name is None and "ffmpeg" in message_lower:
            stage_name = TASK_STAGES[task.task_type][0]

        if stage_name in task.stage_statuses:
            return stage_name
        if len(task.stages) == 1:
            return task.stages[0]
        return None

    def _build_task_config(self, task: TaskInfo) -> AppConfig:
        base_config = self._config_mgr.config
        target_language = str(
            task.params.get("target_language") or base_config.target_language
        )
        generate_transcript = bool(
            task.params.get("generate_transcript", base_config.generate_transcript)
        )
        return replace(
            base_config,
            target_language=target_language,
            generate_transcript=generate_transcript,
        )

    def _resolve_output_dir(self, params: dict[str, Any]) -> Path:
        raw_output_dir = params.get("output_dir")
        if raw_output_dir:
            return Path(str(raw_output_dir)).resolve()
        return self._config_mgr.resolve_output_dir()

    def _resolve_glossary_dir(self) -> Path | None:
        glossary_dir = self._config_mgr.project_root / GLOSSARIES_DIRNAME
        if glossary_dir.exists():
            return glossary_dir
        return None

    def _resolve_glossary_path(self, target_language: str) -> Path | None:
        glossary_dir = self._resolve_glossary_dir()
        if glossary_dir is None:
            return None
        candidate = glossary_dir / f"{target_language}.csv"
        if candidate.exists():
            return candidate
        return None

    def _resolve_font_dir(self) -> Path | None:
        font_dir = self._config_mgr.project_root / FONTS_DIRNAME
        if font_dir.exists():
            return font_dir
        return None

    def _resolve_font_path(self, value: Any, task_config: AppConfig) -> Path | None:
        raw_value = _normalize_path_text(value)
        if raw_value:
            candidate = Path(raw_value)
            if candidate.exists():
                return candidate.resolve()

        font_dir = self._resolve_font_dir()
        if font_dir is None:
            return None

        default_candidate = font_dir / task_config.font_file
        if default_candidate.exists():
            return default_candidate.resolve()
        return None

    def _load_tasks(self) -> dict[str, TaskInfo]:
        from sublingo.gui.models.task_persistence import load_tasks

        return load_tasks(self._persistence_path)

    def _persist_tasks(self) -> None:
        from sublingo.gui.models.task_persistence import save_tasks

        save_tasks(self._tasks, self._persistence_path)

    def _cleanup_worker(self) -> None:
        worker = self._current_worker
        self._current_worker = None
        self._current_task_id = None
        if worker is None:
            return
        wait = getattr(worker, "wait", None)
        if callable(wait):
            wait()
        delete_later = getattr(worker, "deleteLater", None)
        if callable(delete_later):
            delete_later()
