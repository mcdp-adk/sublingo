from __future__ import annotations

from collections.abc import Callable
from enum import Enum

from PySide6.QtCore import QCoreApplication


def _register_i18n_keys() -> None:
    QCoreApplication.translate("TaskType", "Full Workflow")
    QCoreApplication.translate("TaskType", "Download")
    QCoreApplication.translate("TaskType", "Translate")
    QCoreApplication.translate("TaskType", "Softsub")
    QCoreApplication.translate("TaskType", "Hardsub")
    QCoreApplication.translate("TaskType", "Transcript")
    QCoreApplication.translate("TaskType", "Font Subset")
    QCoreApplication.translate("TaskType", "Workflow")
    QCoreApplication.translate("TaskType", "Module")
    QCoreApplication.translate("TaskType", "Single")
    QCoreApplication.translate("TaskType", "Batch")
    QCoreApplication.translate("TaskType", "{scope}: {name}")
    QCoreApplication.translate("TasksPage", "Batch: {completed}/{total} completed")


STAGE_PENDING: str = "pending"
STAGE_ACTIVE: str = "active"
STAGE_DONE: str = "done"
STAGE_ERROR: str = "error"


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
    TaskType.WORKFLOW: "Full Workflow",
    TaskType.DOWNLOAD: "Download",
    TaskType.TRANSLATE: "Translate",
    TaskType.SOFTSUB: "Softsub",
    TaskType.HARDSUB: "Hardsub",
    TaskType.TRANSCRIPT: "Transcript",
    TaskType.FONT_SUBSET: "Font Subset",
}

TASK_SCOPE_WORKFLOW: str = "Workflow"
TASK_SCOPE_MODULE: str = "Module"
TASK_LABEL_TEMPLATE: str = "{scope}: {name}"
TASK_WORKFLOW_SINGLE_LABEL: str = "Single"
TASK_WORKFLOW_BATCH_LABEL: str = "Batch"
TASK_BATCH_SUMMARY_TEMPLATE: str = "Batch: {completed}/{total} completed"

TASK_STAGES: dict[TaskType, list[str]] = {
    TaskType.WORKFLOW: [
        "Download",
        "Translate",
        "Font Subset",
        "Softsub",
        "Transcript",
    ],
    TaskType.DOWNLOAD: ["Download"],
    TaskType.TRANSLATE: ["Segment", "Translate", "Proofread"],
    TaskType.SOFTSUB: ["Softsub"],
    TaskType.HARDSUB: ["Hardsub"],
    TaskType.TRANSCRIPT: ["Transcript"],
    TaskType.FONT_SUBSET: ["Font Subset"],
}

DEFAULT_STAGE_BY_TASK: dict[TaskType, str] = {
    TaskType.DOWNLOAD: "download",
    TaskType.SOFTSUB: "softsub",
    TaskType.HARDSUB: "hardsub",
    TaskType.TRANSCRIPT: "transcript",
    TaskType.FONT_SUBSET: "font_subset",
}

BACKEND_STAGE_TO_DISPLAY: dict[str, str] = {
    "download": "Download",
    "downloading": "Download",
    "finished": "Download",
    "segment": "Segment",
    "segmenting": "Segment",
    "translate": "Translate",
    "translating": "Translate",
    "proofread": "Proofread",
    "proofreading": "Proofread",
    "font": "Font Subset",
    "font_subset": "Font Subset",
    "softsub": "Softsub",
    "mux": "Softsub",
    "hardsub": "Hardsub",
    "burn": "Hardsub",
    "transcript": "Transcript",
    "complete": "Complete",
}


def is_workflow_task(task_type: TaskType) -> bool:
    return task_type == TaskType.WORKFLOW


def format_task_type_label(
    task_type: TaskType,
    translator: Callable[[str], str],
    *,
    is_batch: bool = False,
) -> str:
    if is_workflow_task(task_type):
        scope = translator(TASK_SCOPE_WORKFLOW)
        name = translator(
            TASK_WORKFLOW_BATCH_LABEL if is_batch else TASK_WORKFLOW_SINGLE_LABEL
        )
    else:
        scope = translator(TASK_SCOPE_MODULE)
        name = translator(TASK_TYPE_DISPLAY.get(task_type, "Task"))
    return translator(TASK_LABEL_TEMPLATE).format(scope=scope, name=name)


def format_batch_summary(
    completed: int,
    total: int,
    translator: Callable[[str], str],
) -> str:
    return translator(TASK_BATCH_SUMMARY_TEMPLATE).format(
        completed=completed,
        total=total,
    )
