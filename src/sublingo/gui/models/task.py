from __future__ import annotations

from enum import Enum
from typing import Any

from PySide6.QtCore import QObject, Signal


class TaskType(Enum):
    WORKFLOW = "workflow"
    DOWNLOAD = "download"
    TRANSLATE = "translate"
    SOFTSUB = "softsub"
    HARDSUB = "hardsub"
    TRANSCRIPT = "transcript"
    FONT_SUBSET = "font_subset"


TASK_TYPE_DISPLAY: dict[TaskType, str] = {
    TaskType.WORKFLOW: "完整工作流",
    TaskType.DOWNLOAD: "仅下载",
    TaskType.TRANSLATE: "仅翻译",
    TaskType.SOFTSUB: "仅软字幕",
    TaskType.HARDSUB: "仅硬字幕",
    TaskType.TRANSCRIPT: "仅转录",
    TaskType.FONT_SUBSET: "仅字体子集化",
}


class TaskManager(QObject):
    """Dummy TaskManager for type checking."""

    task_created = Signal(str)
    task_started = Signal(str)
    task_progress = Signal(str, int, int, str)
    task_finished = Signal(str)
    task_failed = Signal(str, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.task_order: list[str] = []

    def create_task(self, task_type: TaskType, params: dict[str, Any]) -> str:
        return "dummy_task_id"

    def get_task(self, task_id: str) -> Any:
        return None
