from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from sublingo.core.config import AppConfig
from sublingo.core.config import ConfigManager
from sublingo.core.downloader import download
from sublingo.core.ffmpeg import hardsub, softsub
from sublingo.core.font import subset_font
from sublingo.core.models import ProgressCallback
from sublingo.core.network_policy import resolve_download_proxy
from sublingo.core.transcript import generate_transcript
from sublingo.core.translator import translate
from sublingo.core.workflow import run_workflow
from sublingo.gui.models.task_info import TaskInfo
from sublingo.gui.models.task_info import normalize_path_text
from sublingo.gui.models.task_types import BACKEND_STAGE_TO_DISPLAY
from sublingo.gui.models.task_types import DEFAULT_STAGE_BY_TASK
from sublingo.gui.models.task_types import TASK_STAGES
from sublingo.gui.models.task_types import TaskStatus
from sublingo.gui.models.task_types import TaskType
from sublingo.gui.workers.task_worker import CallableTaskWorker

TASK_PERSISTENCE_FILENAME: str = "tasks.json"
GLOSSARIES_DIRNAME: str = "glossaries"
FONTS_DIRNAME: str = "fonts"
DEFAULT_FAILURE_MESSAGE: str = "Task failed"
DEFAULT_WORKER_ERROR_MESSAGE: str = "Failed to create task worker"
MILLISECONDS_PER_SECOND: int = 1000


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
        self._current_worker: CallableTaskWorker | QObject | None = None
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
            if task is not None and task.status == TaskStatus.QUEUED:
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

    def _create_worker(self, task: TaskInfo) -> CallableTaskWorker | None:
        runner = self._build_runner(task)
        if runner is None:
            return None
        return CallableTaskWorker(runner, self)

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
                proxy=resolve_download_proxy(task_config),
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
        self,
        task_id: str,
        current: int,
        total: int,
        message: str,
        meta: dict[str, Any],
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
            backend_stage=DEFAULT_STAGE_BY_TASK.get(task.task_type, ""),
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
        stage_name = BACKEND_STAGE_TO_DISPLAY.get(
            backend_stage or DEFAULT_STAGE_BY_TASK.get(task.task_type, "")
        )
        message_lower = message.lower()
        if stage_name is None and "proofread" in message_lower:
            stage_name = "Proofread"
        if stage_name is None and "translat" in message_lower:
            stage_name = "Translate"
        if stage_name is None and "download" in message_lower:
            stage_name = "Download"
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
        raw_value = normalize_path_text(value)
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

    def resume_workflow(self, task_id: str) -> bool:
        """Resume a failed workflow task from checkpoint.

        Args:
            task_id: The ID of the task to resume

        Returns:
            True if resume was initiated, False otherwise
        """
        from sublingo.core.workflow import resume_workflow

        task = self._tasks.get(task_id)
        if task is None:
            return False
        if task.task_type != TaskType.WORKFLOW:
            return False
        if task.status != TaskStatus.FAILED:
            return False

        # Extract project_dir from task params or meta
        project_dir = self._resolve_project_dir(task)
        if project_dir is None:
            return False

        # Build runner for resume_workflow
        task_config = self._build_task_config(task)
        cookie_file = self._config_mgr.cookie_file
        output_dir = self._resolve_output_dir(task.params)
        glossary_dir = self._resolve_glossary_dir()
        font_dir = self._resolve_font_dir()

        runner = lambda progress: resume_workflow(
            project_dir,
            config=task_config,
            cookie_file=cookie_file,
            glossary_dir=glossary_dir,
            font_dir=font_dir,
            output_dir=output_dir,
            progress=progress,
        )

        # Create and run worker
        worker = CallableTaskWorker(runner, self)

        # Reset task state for resume
        task.mark_running()
        task.error = None
        self._current_worker = worker
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

        return True

    def _resolve_project_dir(self, task: TaskInfo) -> Path | None:
        project_dir = task.meta.get("project_dir") or task.params.get("project_dir")
        if project_dir:
            candidate = Path(str(project_dir))
            if candidate.exists():
                return candidate
        return None

    def _cleanup_worker(self) -> None:
        worker = self._current_worker
        self._current_worker = None
        if worker is None:
            return
        if callable(wait := getattr(worker, "wait", None)):
            wait()
        if callable(delete_later := getattr(worker, "deleteLater", None)):
            delete_later()
