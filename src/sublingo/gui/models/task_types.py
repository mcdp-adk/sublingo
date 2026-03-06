from __future__ import annotations

from enum import Enum

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
    TaskType.DOWNLOAD: "Download Only",
    TaskType.TRANSLATE: "Translate Only",
    TaskType.SOFTSUB: "Softsub Only",
    TaskType.HARDSUB: "Hardsub Only",
    TaskType.TRANSCRIPT: "Transcript Only",
    TaskType.FONT_SUBSET: "Font Subset Only",
}

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
