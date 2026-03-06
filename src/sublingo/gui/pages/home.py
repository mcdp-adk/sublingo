from __future__ import annotations

from typing import Any

from PySide6.QtCore import QCoreApplication, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sublingo.core.config import ConfigManager
from sublingo.core.cookie import validate_cookie_file
from sublingo.gui.models.task import TaskManager
from sublingo.gui.models.task_info import format_status_summary
from sublingo.gui.models.task_info import format_task_title
from sublingo.gui.models.task_types import format_task_type_label
from sublingo.gui.models.task_types import TaskType
from sublingo.gui.widgets.batch_preview_dialog import PreviewDialog
from sublingo.gui.widgets.batch_preview_dialog import PreviewFetchWorker
from sublingo.gui.widgets.batch_preview_dialog import extract_playlist_info
from sublingo.gui.widgets.home_task_forms import HomeTaskForms


class HomePage(QWidget):
    navigate_requested = Signal(str)

    def __init__(
        self,
        config_mgr: ConfigManager,
        task_mgr: TaskManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._config_mgr = config_mgr
        self._task_mgr = task_mgr
        self._preview_worker: PreviewFetchWorker | None = None
        self._preview_progress: QProgressDialog | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        layout.addWidget(self._build_create_group())
        layout.addWidget(self._build_tasks_group())
        layout.addStretch(1)

        if self._task_mgr is not None:
            self._connect_task_mgr(self._task_mgr)
        self._update_button_visibility()

    def set_task_manager(self, task_mgr: TaskManager) -> None:
        self._task_mgr = task_mgr
        self._connect_task_mgr(task_mgr)

    def _build_create_group(self) -> QGroupBox:
        group = QGroupBox(self.tr("New Task"))
        layout = QVBoxLayout(group)

        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel(self.tr("Type:")))
        self._task_type = QComboBox()
        for task_type in TaskType:
            label = format_task_type_label(
                task_type,
                lambda text: QCoreApplication.translate("TaskType", text),
            )
            self._task_type.addItem(label, task_type.value)
        self._task_type.currentIndexChanged.connect(self._on_type_changed)
        selector_row.addWidget(self._task_type, stretch=1)
        layout.addLayout(selector_row)

        self._forms = HomeTaskForms(self._config_mgr, self)
        self._form_stack = self._forms.form_stack
        self._workflow_form = self._forms.workflow_form
        self._download_form = self._forms.download_form
        self._translate_form = self._forms.translate_form
        layout.addWidget(self._forms)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self._preview_btn = QPushButton(self.tr("Preview"))
        self._preview_btn.setMinimumWidth(100)
        self._preview_btn.clicked.connect(self._on_preview)
        button_row.addWidget(self._preview_btn)

        self._start_btn = QPushButton(self.tr("Create Task"))
        self._start_btn.setMinimumWidth(120)
        self._start_btn.clicked.connect(self._on_start)
        button_row.addWidget(self._start_btn)
        layout.addLayout(button_row)
        return group

    def _build_tasks_group(self) -> QGroupBox:
        group = QGroupBox(self.tr("Active Tasks"))
        layout = QVBoxLayout(group)
        self._task_list = QListWidget()
        self._task_list.setMaximumHeight(200)
        self._task_list.itemDoubleClicked.connect(self._on_task_double_clicked)
        layout.addWidget(self._task_list)
        return group

    def _connect_task_mgr(self, task_mgr: TaskManager) -> None:
        task_mgr.task_created.connect(self._refresh_task_list)
        task_mgr.task_started.connect(self._refresh_task_list)
        task_mgr.task_progress.connect(self._on_task_progress)
        task_mgr.task_finished.connect(self._refresh_task_list)
        task_mgr.task_failed.connect(self._refresh_task_list)

    def _on_type_changed(self, index: int) -> None:
        self._forms.set_current_index(index)
        self._update_button_visibility()

    def _update_button_visibility(self) -> None:
        self._preview_btn.setVisible(
            self._current_task_type() in (TaskType.WORKFLOW, TaskType.DOWNLOAD)
        )

    def _current_task_type(self) -> TaskType:
        return TaskType(self._task_type.currentData())

    def _needs_cookie_validation(self, task_type: TaskType) -> bool:
        return task_type in (TaskType.WORKFLOW, TaskType.DOWNLOAD)

    def _validate_cookie_if_needed(self, task_type: TaskType) -> bool:
        if not self._needs_cookie_validation(task_type):
            return True
        ok, _message = validate_cookie_file(self._config_mgr.cookie_file)
        if ok:
            return True
        QMessageBox.warning(self, self.tr("Error"), self.tr("Cookie file is invalid"))
        return False

    def _on_preview(self) -> None:
        if self._task_mgr is None:
            return
        task_type = self._current_task_type()
        urls = self._forms.get_urls(task_type)
        if not urls:
            QMessageBox.warning(
                self, self.tr("Error"), self.tr("Please enter at least one URL")
            )
            return
        if not self._validate_cookie_if_needed(task_type):
            return
        self._start_preview_fetch(task_type, urls)

    def _start_preview_fetch(self, task_type: TaskType, urls: list[str]) -> None:
        self._preview_btn.setEnabled(False)
        progress = QProgressDialog(
            self.tr("Fetching video info..."),
            self.tr("Cancel"),
            0,
            len(urls),
            self,
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)
        progress.show()
        self._preview_progress = progress

        worker = PreviewFetchWorker(
            urls,
            cookie_file=self._config_mgr.cookie_file,
            proxy=self._config_mgr.config.proxy or None,
            parent=self,
        )
        self._preview_worker = worker
        worker.progress.connect(self._on_preview_fetch_progress)
        worker.result_ready.connect(
            lambda rows: self._on_preview_fetch_finished(task_type, rows)
        )
        worker.task_error.connect(self._on_preview_fetch_error)
        worker.finished.connect(self._cleanup_preview_worker)
        progress.canceled.connect(worker.requestInterruption)
        worker.start()

    def _on_preview_fetch_progress(self, current: int, total: int, url: str) -> None:
        if self._preview_progress is None:
            return
        self._preview_progress.setMaximum(total)
        self._preview_progress.setValue(current)
        self._preview_progress.setLabelText(
            self.tr("Parsing URL ({current}/{total}):\n{url}").format(
                current=current,
                total=total,
                url=url,
            )
        )

    def _on_preview_fetch_finished(self, task_type: TaskType, rows: list[Any]) -> None:
        if not rows:
            QMessageBox.warning(self, self.tr("Error"), self.tr("No videos found"))
            return
        dialog = PreviewDialog(rows, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        selected_urls = dialog.selected_urls()
        if not selected_urls:
            QMessageBox.warning(
                self, self.tr("Error"), self.tr("Please select at least one video")
            )
            return
        self._create_tasks_for_urls(task_type, selected_urls)
        self.navigate_requested.emit("tasks")

    def _on_preview_fetch_error(self, error_message: str) -> None:
        QMessageBox.warning(
            self,
            self.tr("Error"),
            self.tr("Failed to fetch video info: {error}").format(error=error_message),
        )

    def _cleanup_preview_worker(self) -> None:
        self._preview_btn.setEnabled(True)
        if self._preview_progress is not None:
            self._preview_progress.close()
            self._preview_progress.deleteLater()
            self._preview_progress = None
        if self._preview_worker is not None:
            self._preview_worker.deleteLater()
            self._preview_worker = None

    def _on_start(self) -> None:
        if self._task_mgr is None:
            return
        task_type = self._current_task_type()
        if not self._validate_cookie_if_needed(task_type):
            return
        if task_type in (TaskType.WORKFLOW, TaskType.DOWNLOAD):
            urls = self._forms.get_urls(task_type)
            if not urls:
                QMessageBox.warning(
                    self, self.tr("Error"), self.tr("Please enter at least one URL")
                )
                return
            self._create_tasks_for_urls(task_type, urls)
        else:
            params = self._forms.collect_params(task_type)
            if params is None:
                QMessageBox.warning(
                    self,
                    self.tr("Error"),
                    self.tr("Please fill in all required fields"),
                )
                return
            self._task_mgr.create_task(task_type, params)
        self.navigate_requested.emit("tasks")

    def _create_tasks_for_urls(self, task_type: TaskType, urls: list[str]) -> None:
        if self._task_mgr is None:
            return
        batch_total = len(urls)
        for index, url in enumerate(urls, start=1):
            params = self._forms.collect_params(task_type, url)
            if params is not None:
                params["batch_index"] = index
                params["batch_total"] = batch_total
                self._task_mgr.create_task(task_type, params)

    def _on_task_double_clicked(self, _item: QListWidgetItem) -> None:
        self.navigate_requested.emit("tasks")

    def _on_task_progress(self, task_id: str, *_args: object) -> None:
        self._refresh_task_list(task_id)

    def _refresh_task_list(self, *_args: object) -> None:
        self._task_list.clear()
        if self._task_mgr is None:
            return
        for task_id in reversed(self._task_mgr.task_order):
            task = self._task_mgr.get_task(task_id)
            if task is None:
                continue
            title = format_task_title(
                task,
                lambda text: QCoreApplication.translate("TaskType", text),
            )
            status = format_status_summary(
                task,
                lambda text: QCoreApplication.translate("TaskStatus", text),
            )
            item = QListWidgetItem(f"{title}   {status}")
            item.setData(Qt.ItemDataRole.UserRole, task_id)
            self._task_list.addItem(item)
