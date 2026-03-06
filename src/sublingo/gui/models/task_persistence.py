from __future__ import annotations

import json
import logging
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from sublingo.gui.models.task_info import TaskInfo
from sublingo.gui.models.task_types import STAGE_ERROR
from sublingo.gui.models.task_types import TaskStatus
from sublingo.gui.models.task_types import TaskType

TASKS_PAYLOAD_KEY: str = "tasks"
INTERRUPTED_TASK_ERROR: str = "应用关闭时任务仍在运行"


def save_tasks(tasks: dict[str, TaskInfo], path: Path) -> None:
    payload = {
        TASKS_PAYLOAD_KEY: [_serialize_task(task) for task in tasks.values()],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_tasks(path: Path) -> dict[str, TaskInfo]:
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    raw_tasks = payload.get(TASKS_PAYLOAD_KEY, []) if isinstance(payload, dict) else []
    if not isinstance(raw_tasks, list):
        return {}

    loaded: dict[str, TaskInfo] = {}
    for item in raw_tasks:
        if not isinstance(item, dict):
            continue
        task = _deserialize_task(item)
        loaded[task.id] = task
    return loaded


def _serialize_task(task: TaskInfo) -> dict[str, Any]:
    return {
        "id": task.id,
        "task_type": task.task_type.value,
        "params": _serialize_value(task.params),
        "status": task.status.value,
        "created_at": task.created_at.isoformat(),
        "stages": list(task.stages),
        "stage_statuses": _serialize_value(task.stage_statuses),
        "current_stage": task.current_stage,
        "progress_percent": task.progress_percent,
        "progress_message": task.progress_message,
        "meta": _serialize_value(task.meta),
        "result": _serialize_value(task.result),
        "error": task.error,
        "video_title": task.video_title,
    }


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {
            field.name: _serialize_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _deserialize_task(payload: dict[str, Any]) -> TaskInfo:
    task = TaskInfo(
        id=str(payload.get("id") or ""),
        task_type=TaskType(payload.get("task_type", TaskType.WORKFLOW.value)),
        params=dict(payload.get("params") or {}),
        status=TaskStatus(payload.get("status", TaskStatus.QUEUED.value)),
        created_at=_parse_datetime(payload.get("created_at")),
        stages=list(payload.get("stages") or []),
        stage_statuses=dict(payload.get("stage_statuses") or {}),
        current_stage=str(payload.get("current_stage") or ""),
        progress_percent=int(payload.get("progress_percent") or 0),
        progress_message=str(payload.get("progress_message") or ""),
        meta=dict(payload.get("meta") or {}),
        result=payload.get("result"),
        error=payload.get("error"),
        video_title=str(payload.get("video_title") or ""),
    )

    if task.status == TaskStatus.RUNNING:
        task.status = TaskStatus.FAILED
        task.error = task.error or INTERRUPTED_TASK_ERROR
        if task.current_stage in task.stage_statuses:
            task.stage_statuses[task.current_stage] = STAGE_ERROR

    return task


def _parse_datetime(raw_value: Any) -> datetime:
    if isinstance(raw_value, str) and raw_value:
        try:
            return datetime.fromisoformat(raw_value)
        except ValueError:
            logger.debug("Failed to parse datetime from value: %r", raw_value)
    return datetime.now(timezone.utc)
