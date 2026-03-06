"""Task monitoring interface."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QProgressBar,
)

from sublingo.gui.models.task import TaskManager
from sublingo.gui.models.task_types import TaskStatus
from sublingo.gui.widgets.log_viewer import LogViewer
from sublingo.gui.widgets.stepper import Stepper


class TaskItemWidget(QWidget):
    """Custom widget for task list item."""

    def __init__(self, task: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        title = getattr(task, "video_title", "") or getattr(
            task, "display_name", "Unknown Task"
        )
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.title_label)

        status_layout = QHBoxLayout()
        self.type_label = QLabel(str(getattr(task, "task_type", "")))
        self.status_label = QLabel(getattr(task, "status_summary", ""))
        status_layout.addWidget(self.type_label)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(getattr(task, "progress_percent", 0))
        layout.addWidget(self.progress_bar)

    def update_task(self, task: Any) -> None:
        title = getattr(task, "video_title", "") or getattr(
            task, "display_name", "Unknown Task"
        )
        self.title_label.setText(title)
        self.type_label.setText(str(getattr(task, "task_type", "")))
        self.status_label.setText(getattr(task, "status_summary", ""))
        self.progress_bar.setValue(getattr(task, "progress_percent", 0))


class TaskDetailWidget(QWidget):
    """Detail view for a single task."""

    def __init__(
        self, parent: QWidget | None = None, *, debug_mode: bool = False
    ) -> None:
        super().__init__(parent)
        self._debug_mode = debug_mode
        self._current_task_id: str | None = None

        layout = QVBoxLayout(self)

        # Video info card
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        # Stepper
        self.stepper = Stepper()
        layout.addWidget(self.stepper)

        # Stage detail area
        self.stage_detail_label = QLabel()
        layout.addWidget(self.stage_detail_label)

        # Continue button
        self.continue_btn = QPushButton(self.tr("Continue"))
        self.continue_btn.hide()
        layout.addWidget(self.continue_btn)

        # Log panel
        self.log_viewer = LogViewer(debug_mode=debug_mode)
        layout.addWidget(self.log_viewer, stretch=1)

    def show_task(self, task: Any) -> None:
        self._current_task_id = getattr(task, "id", None)

        # Update info card
        title = getattr(task, "video_title", "") or getattr(
            task, "display_name", "Unknown Task"
        )
        channel = getattr(task, "channel", "")
        duration = getattr(task, "duration", "")
        upload_date = getattr(task, "upload_date", "")
        video_id = getattr(task, "video_id", "")

        info_text = f"<b>{title}</b><br>"
        if channel:
            info_text += f"Channel: {channel} | "
        if duration:
            info_text += f"Duration: {duration} | "
        if upload_date:
            info_text += f"Date: {upload_date} | "
        if video_id:
            info_text += f"ID: {video_id}"
        self.info_label.setText(info_text)

        # Update stepper
        stages = getattr(task, "stages", [])
        self.stepper.set_stages(stages)
        stage_statuses = getattr(task, "stage_statuses", {})
        for stage in stages:
            status = stage_statuses.get(stage, "pending")
            self.stepper.set_stage_status(stage, status)

        # Update stage detail
        self.stage_detail_label.setText(getattr(task, "progress_message", ""))

        # Update continue button
        status = getattr(task, "status", None)
        if status and str(status).endswith("FAILED"):
            self.continue_btn.show()
        else:
            self.continue_btn.hide()

        self.log_viewer.clear_logs()

    def update_progress(self, task: Any) -> None:
        if getattr(task, "id", None) != self._current_task_id:
            return

        stages = getattr(task, "stages", [])
        stage_statuses = getattr(task, "stage_statuses", {})
        for stage in stages:
            status = stage_statuses.get(stage, "pending")
            self.stepper.set_stage_status(stage, status)

        self.stage_detail_label.setText(getattr(task, "progress_message", ""))

        status = getattr(task, "status", None)
        if status and str(status).endswith("FAILED"):
            self.continue_btn.show()
        else:
            self.continue_btn.hide()

    def append_log(
        self, task_id: str, level: str, message: str, detail: str = ""
    ) -> None:
        if task_id == self._current_task_id:
            self.log_viewer.append_log(level, message, detail)


class TasksPage(QWidget):
    """Task monitoring interface."""

    def __init__(
        self,
        task_mgr: TaskManager,
        parent: QWidget | None = None,
        *,
        debug_mode: bool = False,
    ) -> None:
        super().__init__(parent)
        self._task_mgr = task_mgr

        layout = QVBoxLayout(self)

        self.batch_summary_label = QLabel()
        self.batch_summary_label.hide()
        layout.addWidget(self.batch_summary_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left panel: Task list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.task_list = QListWidget()
        self.task_list.itemSelectionChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.task_list)

        splitter.addWidget(left_panel)

        # Right panel: Task detail
        self.detail_widget = TaskDetailWidget(debug_mode=debug_mode)
        self.detail_widget.continue_btn.clicked.connect(self._on_continue_clicked)
        splitter.addWidget(self.detail_widget)

        splitter.setSizes([300, 500])

        # Connect signals
        self._task_mgr.task_created.connect(self._refresh_list)
        self._task_mgr.task_started.connect(self._refresh_list)
        self._task_mgr.task_progress.connect(self._on_progress)

        # Check if task_log exists before connecting
        if hasattr(self._task_mgr, "task_log"):
            self._task_mgr.task_log.connect(self._on_log)

        self._task_mgr.task_finished.connect(self._on_task_done)
        self._task_mgr.task_failed.connect(self._on_task_done)

        self._item_widgets: dict[str, TaskItemWidget] = {}
        self._refresh_list()

    def _refresh_list(self, *_args: object) -> None:
        self.task_list.clear()
        self._item_widgets.clear()
        self._update_batch_summary()

        for tid in reversed(self._task_mgr.task_order):
            task = self._task_mgr.get_task(tid)
            if task is None:
                continue

            item = QListWidgetItem(self.task_list)
            item.setData(Qt.ItemDataRole.UserRole, tid)

            widget = TaskItemWidget(task)
            item.setSizeHint(widget.sizeHint())
            self.task_list.setItemWidget(item, widget)
            self._item_widgets[tid] = widget

    def _update_batch_summary(self) -> None:
        total = len(self._task_mgr.task_order)
        if total <= 1:
            self.batch_summary_label.hide()
            self.batch_summary_label.clear()
            return

        completed = 0
        for tid in self._task_mgr.task_order:
            task = self._task_mgr.get_task(tid)
            if task is not None and task.status == TaskStatus.COMPLETED:
                completed += 1

        self.batch_summary_label.setText(f"Batch: {completed}/{total} completed")
        self.batch_summary_label.show()

    def _on_selection_changed(self) -> None:
        items = self.task_list.selectedItems()
        if not items:
            return
        tid = items[0].data(Qt.ItemDataRole.UserRole)
        task = self._task_mgr.get_task(tid)
        if task:
            self.detail_widget.show_task(task)

    def _on_progress(
        self, task_id: str, current: int, total: int, msg: str, meta: dict | None = None
    ) -> None:
        task = self._task_mgr.get_task(task_id)
        if task:
            if task_id in self._item_widgets:
                self._item_widgets[task_id].update_task(task)
            self.detail_widget.update_progress(task)

    def _on_log(self, task_id: str, level: str, msg: str, detail: str = "") -> None:
        self.detail_widget.append_log(task_id, level, msg, detail)

    def _on_task_done(self, task_id: str, *_args: object) -> None:
        task = self._task_mgr.get_task(task_id)
        if task:
            if task_id in self._item_widgets:
                self._item_widgets[task_id].update_task(task)
            self.detail_widget.update_progress(task)

    def _on_continue_clicked(self) -> None:
        # Call resume_workflow if available
        if not self.detail_widget._current_task_id:
            return
        resume_workflow = getattr(self._task_mgr, "resume_workflow", None)
        if callable(resume_workflow):
            resume_workflow(self.detail_widget._current_task_id)
