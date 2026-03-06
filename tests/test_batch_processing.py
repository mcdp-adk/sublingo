from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Qt, Signal

from sublingo.core.config import AppConfig, ConfigManager
from sublingo.core.models import DownloadResult
from sublingo.gui.models.task import TaskManager
from sublingo.gui.models.task_types import TaskStatus, TaskType
from sublingo.gui.pages.tasks import TasksPage
from sublingo.gui.widgets.batch_preview_dialog import PreviewDialog, PreviewVideoRow


class _ManualWorker(QObject):
    progress = Signal(int, int, str, dict)
    log = Signal(str, str, str)
    result_ready = Signal(object)
    task_error = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.started = False

    def start(self) -> None:
        self.started = True

    def wait(self) -> None:
        return


def test_preview_dialog_selected_urls(qtbot: Any) -> None:
    rows = [
        PreviewVideoRow(
            url="https://example.com/1",
            title="Video 1",
            duration=65,
            has_subtitles=True,
        ),
        PreviewVideoRow(
            url="https://example.com/2",
            title="Video 2",
            duration=130,
            has_subtitles=False,
        ),
    ]

    dialog = PreviewDialog(rows)
    qtbot.addWidget(dialog)

    first_item = dialog._table.item(0, 0)
    assert first_item is not None
    first_item.setCheckState(Qt.CheckState.Unchecked)

    assert dialog.selected_urls() == ["https://example.com/2"]


def test_task_manager_respects_batch_delay_between_tasks(
    tmp_path: Path, monkeypatch: Any, qtbot: Any
) -> None:
    config_mgr = ConfigManager(tmp_path)
    config_mgr.save(AppConfig(batch_delay_seconds=1))
    manager = TaskManager(config_mgr, persistence_path=tmp_path / "tasks.json")

    workers: dict[str, _ManualWorker] = {}

    def fake_create_worker(task: Any) -> _ManualWorker:
        worker = _ManualWorker()
        workers[task.id] = worker
        return worker

    monkeypatch.setattr(manager, "_create_worker", fake_create_worker)

    first_id = manager.create_task(TaskType.DOWNLOAD, {"url": "https://example.com/1"})
    second_id = manager.create_task(TaskType.DOWNLOAD, {"url": "https://example.com/2"})

    assert workers[first_id].started is True
    assert second_id not in workers

    workers[first_id].result_ready.emit(
        DownloadResult(success=True, video_title="Video 1")
    )

    assert second_id not in workers

    qtbot.waitUntil(
        lambda: second_id in workers and workers[second_id].started,
        timeout=2500,
    )


def test_tasks_page_shows_batch_progress_summary(
    tmp_path: Path, monkeypatch: Any, qtbot: Any
) -> None:
    config_mgr = ConfigManager(tmp_path)
    manager = TaskManager(config_mgr, persistence_path=tmp_path / "tasks.json")

    def fake_create_worker(_task: Any) -> _ManualWorker:
        return _ManualWorker()

    monkeypatch.setattr(manager, "_create_worker", fake_create_worker)

    first_id = manager.create_task(TaskType.DOWNLOAD, {"url": "https://example.com/1"})
    second_id = manager.create_task(TaskType.DOWNLOAD, {"url": "https://example.com/2"})

    first_task = manager.get_task(first_id)
    second_task = manager.get_task(second_id)
    assert first_task is not None
    assert second_task is not None

    first_task.status = TaskStatus.COMPLETED
    second_task.status = TaskStatus.RUNNING

    page = TasksPage(manager)
    qtbot.addWidget(page)
    page._refresh_list()

    assert page.batch_summary_label.isHidden() is False
    assert page.batch_summary_label.text() == "Batch: 1/2 completed"
