from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PySide6.QtCore import QCoreApplication, QObject, Signal

from sublingo.core.config import ConfigManager
from sublingo.core.models import DownloadResult
from sublingo.gui.models.task import TASK_STAGES
from sublingo.gui.models.task import TaskInfo
from sublingo.gui.models.task import TaskManager
from sublingo.gui.models.task import TaskStatus
from sublingo.gui.models.task import TaskType
from sublingo.gui.models.task_persistence import load_tasks
from sublingo.gui.models.task_persistence import save_tasks


def _get_app() -> QCoreApplication:
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


class _ManualWorker(QObject):
    progress = Signal(int, int, str, dict)
    log = Signal(str, str, str)
    result_ready = Signal(object)
    task_error = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.started = False
        self.wait_calls = 0

    def start(self) -> None:
        self.started = True

    def wait(self) -> None:
        self.wait_calls += 1


def test_task_info_state_transitions() -> None:
    task = TaskInfo(
        task_type=TaskType.TRANSLATE,
        params={"subtitle_file": "demo.srt"},
    )

    assert task.status == TaskStatus.QUEUED
    assert task.stages == TASK_STAGES[TaskType.TRANSLATE]
    assert task.stage_statuses == {
        "分段": "pending",
        "翻译": "pending",
        "校对": "pending",
    }

    task.mark_running()

    assert task.status == TaskStatus.RUNNING
    assert task.current_stage == "分段"
    assert task.stage_statuses["分段"] == "active"

    task.update_progress(
        current=1,
        total=2,
        message="Translating batch 1/2",
        meta={"stage": "translating"},
        stage_name="翻译",
    )

    assert task.current_stage == "翻译"
    assert task.stage_statuses["分段"] == "done"
    assert task.stage_statuses["翻译"] == "active"
    assert task.progress_percent == 49

    task.mark_failed("boom", failed_stage="校对")

    assert task.status == TaskStatus.FAILED
    assert task.error == "boom"
    assert task.current_stage == "校对"
    assert task.stage_statuses["校对"] == "error"

    completed = TaskInfo(
        task_type=TaskType.DOWNLOAD, params={"url": "https://example.com"}
    )
    completed.mark_running()
    completed.mark_completed({"ok": True})

    assert completed.status == TaskStatus.COMPLETED
    assert completed.progress_percent == 100
    assert completed.stage_statuses == {"下载": "done"}


def test_task_manager_create_queue_and_run_lifecycle(
    tmp_path: Path, monkeypatch: Any
) -> None:
    _get_app()
    persistence_path = tmp_path / "tasks.json"
    config_mgr = ConfigManager(tmp_path)
    manager = TaskManager(config_mgr, persistence_path=persistence_path)
    workers: dict[str, _ManualWorker] = {}
    events: list[tuple[str, str]] = []
    logs: list[tuple[str, str, str, str]] = []

    def fake_create_worker(task: TaskInfo) -> _ManualWorker:
        worker = _ManualWorker()
        workers[task.id] = worker
        return worker

    monkeypatch.setattr(manager, "_create_worker", fake_create_worker)
    manager.task_created.connect(lambda task_id: events.append(("created", task_id)))
    manager.task_started.connect(lambda task_id: events.append(("started", task_id)))
    manager.task_finished.connect(lambda task_id: events.append(("finished", task_id)))
    manager.task_failed.connect(
        lambda task_id, _msg: events.append(("failed", task_id))
    )
    manager.task_log.connect(
        lambda task_id, level, message, detail: logs.append(
            (task_id, level, message, detail)
        )
    )

    first_id = manager.create_task(TaskType.DOWNLOAD, {"url": "https://example.com/1"})

    first_task = manager.get_task(first_id)
    assert first_task is not None
    assert first_task.status == TaskStatus.RUNNING
    assert workers[first_id].started is True

    second_id = manager.create_task(TaskType.DOWNLOAD, {"url": "https://example.com/2"})

    second_task = manager.get_task(second_id)
    assert second_task is not None
    assert second_task.status == TaskStatus.QUEUED
    assert second_id not in workers

    workers[first_id].progress.emit(5, 10, "downloading", {})
    workers[first_id].log.emit("info", "download log", "detail")

    first_task = manager.get_task(first_id)
    assert first_task is not None
    assert first_task.current_stage == "下载"
    assert first_task.progress_percent == 50

    workers[first_id].result_ready.emit(
        DownloadResult(success=True, video_title="Video 1")
    )

    first_task = manager.get_task(first_id)
    second_task = manager.get_task(second_id)
    assert first_task is not None
    assert second_task is not None
    assert first_task.status == TaskStatus.COMPLETED
    assert first_task.video_title == "Video 1"
    assert second_task.status == TaskStatus.RUNNING
    assert workers[first_id].wait_calls == 1
    assert workers[second_id].started is True

    workers[second_id].task_error.emit(RuntimeError("boom"))

    second_task = manager.get_task(second_id)
    assert second_task is not None
    assert second_task.status == TaskStatus.FAILED
    assert second_task.error == "boom"
    assert workers[second_id].wait_calls == 1
    assert logs == [(first_id, "info", "download log", "detail")]
    assert events == [
        ("created", first_id),
        ("started", first_id),
        ("created", second_id),
        ("finished", first_id),
        ("started", second_id),
        ("failed", second_id),
    ]

    persisted = load_tasks(persistence_path)
    assert persisted[first_id].status == TaskStatus.COMPLETED
    assert persisted[second_id].status == TaskStatus.FAILED


def test_task_manager_loads_persisted_tasks_on_startup(tmp_path: Path) -> None:
    _get_app()
    created_at = datetime(2026, 3, 6, 12, 0, tzinfo=timezone.utc)
    persistence_path = tmp_path / "tasks.json"
    queued = TaskInfo(
        id="queued123",
        task_type=TaskType.TRANSCRIPT,
        params={"subtitle_file": "demo.srt"},
        created_at=created_at,
    )
    finished = TaskInfo(
        id="done456",
        task_type=TaskType.SOFTSUB,
        params={
            "video_file": tmp_path / "video.mkv",
            "subtitle_file": tmp_path / "demo.ass",
        },
        status=TaskStatus.COMPLETED,
        created_at=created_at,
        current_stage="软字幕",
        progress_percent=100,
        progress_message="done",
        meta={"output_path": tmp_path / "video.softsub.mkv"},
        result={"output_path": tmp_path / "video.softsub.mkv"},
        video_title="Demo",
    )
    finished.stage_statuses["软字幕"] = "done"

    save_tasks({queued.id: queued, finished.id: finished}, persistence_path)

    manager = TaskManager(ConfigManager(tmp_path), persistence_path=persistence_path)
    finished_task = manager.get_task(finished.id)

    assert manager.task_order == [queued.id, finished.id]
    assert manager.get_task(queued.id) is not None
    assert finished_task is not None
    assert finished_task.task_type == TaskType.SOFTSUB
    assert finished_task.created_at == created_at
    assert finished_task.params["video_file"] == str(tmp_path / "video.mkv")
    assert finished_task.meta["output_path"] == str(tmp_path / "video.softsub.mkv")
    assert finished_task.result == {"output_path": str(tmp_path / "video.softsub.mkv")}
