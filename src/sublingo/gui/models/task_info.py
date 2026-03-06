from __future__ import annotations

from collections.abc import Callable
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sublingo.gui.models.task_types import STAGE_ACTIVE
from sublingo.gui.models.task_types import STAGE_DONE
from sublingo.gui.models.task_types import STAGE_ERROR
from sublingo.gui.models.task_types import STAGE_PENDING
from sublingo.gui.models.task_types import TASK_STAGES
from sublingo.gui.models.task_types import format_task_type_label
from sublingo.gui.models.task_types import TaskStatus
from sublingo.gui.models.task_types import TaskType


def normalize_path_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Path):
        return str(value)
    return ""


def describe_task(task: "TaskInfo") -> str:
    for key in ("url", "subtitle_file", "video_file", "font_file"):
        value = normalize_path_text(task.params.get(key))
        if not value:
            continue
        if key == "url":
            return value
        return Path(value).name
    return ""


def _as_positive_int(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def get_batch_total(task: "TaskInfo") -> int:
    return _as_positive_int(task.params.get("batch_total"), 1)


def get_batch_index(task: "TaskInfo") -> int:
    return _as_positive_int(task.params.get("batch_index"), 1)


def is_batch_task(task: "TaskInfo") -> bool:
    return get_batch_total(task) > 1


def format_task_title(task: "TaskInfo", translator: Callable[[str], str]) -> str:
    title = format_task_type_label(
        task.task_type,
        translator,
        is_batch=is_batch_task(task),
    )
    suffix = task.video_title or describe_task(task)
    if not suffix:
        return title
    return f"{title}  {suffix}"


def format_status_summary(task: "TaskInfo", translator: Callable[[str], str]) -> str:
    if task.status == TaskStatus.COMPLETED:
        return translator("Completed")
    if task.status == TaskStatus.FAILED:
        return translator("Failed")
    if task.status == TaskStatus.RUNNING and task.current_stage:
        stage = translator(task.current_stage)
        if task.progress_percent > 0:
            return translator("{stage} {percent}%").format(
                stage=stage,
                percent=task.progress_percent,
            )
        return stage
    return translator("Queued")


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

        self.stage_statuses = {
            stage: self.stage_statuses.get(stage, STAGE_PENDING)
            for stage in self.stages
        }
        if self.current_stage and self.current_stage not in self.stage_statuses:
            self.current_stage = ""

    @property
    def display_name(self) -> str:
        task_name = format_task_type_label(
            self.task_type,
            lambda text: text,
            is_batch=is_batch_task(self),
        )
        suffix = self.video_title or describe_task(self)
        if not suffix:
            return task_name
        return f"{task_name}  {suffix}"

    @property
    def status_summary(self) -> str:
        if self.status == TaskStatus.COMPLETED:
            return "Completed"
        if self.status == TaskStatus.FAILED:
            return "Failed"
        if self.status == TaskStatus.RUNNING and self.current_stage:
            if self.progress_percent > 0:
                return f"{self.current_stage} {self.progress_percent}%"
            return self.current_stage
        return "Queued"

    def mark_queued(self) -> None:
        self.status = TaskStatus.QUEUED
        self.progress_message = "Queued"
        self.error = None

    def mark_running(self) -> None:
        self.status = TaskStatus.RUNNING
        self.progress_message = "Running"
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
            if str(meta.get("stage_status") or "") == STAGE_DONE:
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
