"""Home page -- dashboard with quick task creation and active task preview."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QCoreApplication, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from sublingo.core.config import ConfigManager
from sublingo.core.cookie import validate_cookie_file
from sublingo.core.downloader import extract_playlist_info
from sublingo.gui.models.task import TASK_TYPE_DISPLAY, TaskManager, TaskType
from sublingo.gui.widgets.file_picker import FilePicker
from sublingo.gui.widgets.form_row import FormRow

# Target languages (shared with settings, but kept local for now).
_TARGET_LANGUAGES: dict[str, str] = {
    "zh-Hans": "简体中文",
    "zh-Hant": "繁體中文",
    "ja": "日本語",
    "ko": "한국어",
    "en": "English",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
    "pt": "Português",
    "ru": "Русский",
}


class PreviewDialog(QDialog):
    """Dialog to preview and confirm videos in a playlist."""

    def __init__(self, videos: list[Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("预览视频列表"))
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        self._list = QListWidget()
        for video in videos:
            item = QListWidgetItem(f"{video.title} ({video.duration}s)")
            item.setData(Qt.ItemDataRole.UserRole, video.url)
            self._list.addItem(item)
        layout.addWidget(self._list)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)


class HomePage(QWidget):
    """Dashboard: quick task creation + active task preview."""

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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # -- Quick create section --
        create_group = QGroupBox(self.tr("新建任务"))
        create_layout = QVBoxLayout(create_group)

        # Task type selector
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel(self.tr("类型:")))
        self._task_type = QComboBox()
        for tt in TaskType:
            name = TASK_TYPE_DISPLAY[tt]
            translated_name = QCoreApplication.translate("TaskType", name)
            self._task_type.addItem(translated_name, tt.value)
        self._task_type.currentIndexChanged.connect(self._on_type_changed)
        type_row.addWidget(self._task_type, stretch=1)
        create_layout.addLayout(type_row)

        # Dynamic form area (stacked widget for different task types)
        self._form_stack = QStackedWidget()
        self._form_stack.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )

        # Workflow form
        self._workflow_form = self._build_workflow_form()
        self._form_stack.addWidget(self._workflow_form)

        # Download form
        self._download_form = self._build_download_form()
        self._form_stack.addWidget(self._download_form)

        # Translate form
        self._translate_form = self._build_translate_form()
        self._form_stack.addWidget(self._translate_form)

        # Softsub form
        self._softsub_form = self._build_softsub_form()
        self._form_stack.addWidget(self._softsub_form)

        # Hardsub form
        self._hardsub_form = self._build_hardsub_form()
        self._form_stack.addWidget(self._hardsub_form)

        # Transcript form
        self._transcript_form = self._build_transcript_form()
        self._form_stack.addWidget(self._transcript_form)

        # Font Subset form
        self._font_subset_form = self._build_font_subset_form()
        self._form_stack.addWidget(self._font_subset_form)

        create_layout.addWidget(self._form_stack)

        # Apply config defaults to forms
        self._apply_config_defaults()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self._preview_btn = QPushButton(self.tr("预览"))
        self._preview_btn.setMinimumWidth(100)
        self._preview_btn.clicked.connect(self._on_preview)
        btn_row.addWidget(self._preview_btn)

        self._start_btn = QPushButton(self.tr("创建任务"))
        self._start_btn.setMinimumWidth(120)
        self._start_btn.clicked.connect(self._on_start)
        btn_row.addWidget(self._start_btn)
        create_layout.addLayout(btn_row)

        layout.addWidget(create_group)

        # -- Active tasks section --
        tasks_group = QGroupBox(self.tr("活动任务"))
        tasks_layout = QVBoxLayout(tasks_group)
        self._task_list = QListWidget()
        self._task_list.setMaximumHeight(200)
        self._task_list.itemDoubleClicked.connect(self._on_task_double_clicked)
        tasks_layout.addWidget(self._task_list)
        layout.addWidget(tasks_group)

        layout.addStretch(1)

        # Connect to TaskManager signals
        if self._task_mgr:
            self._connect_task_mgr(self._task_mgr)

        self._update_button_visibility()

    def set_task_manager(self, task_mgr: TaskManager) -> None:
        """Set or replace the task manager (for deferred injection)."""
        self._task_mgr = task_mgr
        self._connect_task_mgr(task_mgr)

    def _connect_task_mgr(self, task_mgr: TaskManager) -> None:
        task_mgr.task_created.connect(self._refresh_task_list)
        task_mgr.task_started.connect(self._refresh_task_list)
        task_mgr.task_progress.connect(self._on_task_progress)
        task_mgr.task_finished.connect(self._refresh_task_list)
        task_mgr.task_failed.connect(self._refresh_task_list)

    # -- Form builders --

    def _build_workflow_form(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 4, 0, 0)
        self._wf_url = QTextEdit()
        self._wf_url.setPlaceholderText(
            self.tr("输入视频 URL 或 YouTube 播放列表 URL (每行一个)")
        )
        self._wf_url.setMaximumHeight(80)
        layout.addWidget(FormRow(self.tr("URL:"), self._wf_url))

        self._wf_lang = QComboBox()
        for code, name in _TARGET_LANGUAGES.items():
            self._wf_lang.addItem(f"{name} ({code})", code)
        layout.addWidget(FormRow(self.tr("目标语言:"), self._wf_lang))

        self._wf_transcript = QCheckBox(self.tr("生成转录文本"))
        layout.addWidget(FormRow("", self._wf_transcript))
        return w

    def _build_download_form(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 4, 0, 0)
        self._dl_url = QTextEdit()
        self._dl_url.setPlaceholderText(
            self.tr("输入视频 URL 或 YouTube 播放列表 URL (每行一个)")
        )
        self._dl_url.setMaximumHeight(80)
        layout.addWidget(FormRow(self.tr("URL:"), self._dl_url))
        return w

    def _build_translate_form(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 4, 0, 0)
        self._tr_file = FilePicker(
            mode="file", filter=self.tr("Subtitles (*.srt *.vtt *.ass)")
        )
        layout.addWidget(FormRow(self.tr("字幕文件:"), self._tr_file))
        self._tr_lang = QComboBox()
        for code, name in _TARGET_LANGUAGES.items():
            self._tr_lang.addItem(f"{name} ({code})", code)
        layout.addWidget(FormRow(self.tr("目标语言:"), self._tr_lang))
        return w

    def _build_softsub_form(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 4, 0, 0)
        self._ss_video = FilePicker(
            mode="file", filter=self.tr("Video (*.mp4 *.mkv *.webm *.mov *.avi)")
        )
        layout.addWidget(FormRow(self.tr("视频文件:"), self._ss_video))
        self._ss_sub = FilePicker(
            mode="file", filter=self.tr("Subtitles (*.srt *.vtt *.ass)")
        )
        layout.addWidget(FormRow(self.tr("字幕文件:"), self._ss_sub))
        self._ss_font = FilePicker(
            mode="file", filter=self.tr("Font (*.ttf *.otf *.woff *.woff2)")
        )
        layout.addWidget(FormRow(self.tr("字体文件 (可选):"), self._ss_font))
        return w

    def _build_hardsub_form(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 4, 0, 0)
        self._hs_video = FilePicker(
            mode="file", filter=self.tr("Video (*.mp4 *.mkv *.webm *.mov *.avi)")
        )
        layout.addWidget(FormRow(self.tr("视频文件:"), self._hs_video))
        self._hs_sub = FilePicker(
            mode="file", filter=self.tr("Subtitles (*.srt *.vtt *.ass)")
        )
        layout.addWidget(FormRow(self.tr("字幕文件:"), self._hs_sub))
        self._hs_font = FilePicker(
            mode="file", filter=self.tr("Font (*.ttf *.otf *.woff *.woff2)")
        )
        layout.addWidget(FormRow(self.tr("字体文件 (可选):"), self._hs_font))
        return w

    def _build_transcript_form(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 4, 0, 0)
        self._tc_file = FilePicker(
            mode="file", filter=self.tr("Subtitles (*.srt *.vtt *.ass)")
        )
        layout.addWidget(FormRow(self.tr("字幕文件:"), self._tc_file))
        return w

    def _build_font_subset_form(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 4, 0, 0)
        self._fs_sub = FilePicker(
            mode="file", filter=self.tr("Subtitles (*.srt *.vtt *.ass)")
        )
        layout.addWidget(FormRow(self.tr("字幕文件:"), self._fs_sub))
        self._fs_font = FilePicker(
            mode="file", filter=self.tr("Font (*.ttf *.otf *.woff *.woff2)")
        )
        layout.addWidget(FormRow(self.tr("字体文件:"), self._fs_font))
        return w

    def _apply_config_defaults(self) -> None:
        """Fill form fields with defaults from configuration."""
        cfg = self._config_mgr.config

        # Workflow: transcript checkbox
        self._wf_transcript.setChecked(cfg.generate_transcript)

        # Workflow: target language
        idx = self._wf_lang.findData(cfg.target_language)
        if idx >= 0:
            self._wf_lang.setCurrentIndex(idx)

        # Translate: target language
        idx = self._tr_lang.findData(cfg.target_language)
        if idx >= 0:
            self._tr_lang.setCurrentIndex(idx)

        # Font file
        font_path = self._config_mgr.project_root / "fonts" / cfg.font_file
        if font_path.exists():
            self._ss_font.set_path(str(font_path))
            self._hs_font.set_path(str(font_path))
            self._fs_font.set_path(str(font_path))

    # -- Slots --

    def _on_type_changed(self, index: int) -> None:
        self._form_stack.setCurrentIndex(index)
        self._update_button_visibility()

    def _update_button_visibility(self) -> None:
        task_type_value = self._task_type.currentData()
        task_type = TaskType(task_type_value)
        if task_type in (TaskType.WORKFLOW, TaskType.DOWNLOAD):
            self._preview_btn.setVisible(True)
        else:
            self._preview_btn.setVisible(False)

    def _get_urls(self, task_type: TaskType) -> list[str]:
        if task_type == TaskType.WORKFLOW:
            text = self._wf_url.toPlainText()
        elif task_type == TaskType.DOWNLOAD:
            text = self._dl_url.toPlainText()
        else:
            return []
        return [line.strip() for line in text.splitlines() if line.strip()]

    def _on_preview(self) -> None:
        task_type_value = self._task_type.currentData()
        task_type = TaskType(task_type_value)
        urls = self._get_urls(task_type)

        if not urls:
            QMessageBox.warning(self, self.tr("错误"), self.tr("请输入至少一个 URL"))
            return

        # Cookie check
        ok, _msg = validate_cookie_file(self._config_mgr.cookie_file)
        if not ok:
            QMessageBox.warning(self, self.tr("错误"), self.tr("Cookie 文件无效"))
            return

        all_videos = []
        try:
            for url in urls:
                videos = extract_playlist_info(
                    url,
                    cookie_file=self._config_mgr.cookie_file,
                    proxy=self._config_mgr.config.proxy or None,
                )
                all_videos.extend(videos)
        except Exception as e:
            QMessageBox.warning(
                self, self.tr("错误"), self.tr(f"获取视频信息失败: {e}")
            )
            return

        if not all_videos:
            QMessageBox.warning(self, self.tr("错误"), self.tr("未找到任何视频"))
            return

        dialog = PreviewDialog(all_videos, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # If accepted, we could automatically start the task, but for now just close dialog
            pass

    def _on_start(self) -> None:
        if self._task_mgr is None:
            return

        task_type_value = self._task_type.currentData()
        task_type = TaskType(task_type_value)

        # Cookie check for types that need it
        if task_type in (TaskType.WORKFLOW, TaskType.DOWNLOAD):
            ok, _msg = validate_cookie_file(self._config_mgr.cookie_file)
            if not ok:
                QMessageBox.warning(self, self.tr("错误"), self.tr("Cookie 文件无效"))
                return

        if task_type in (TaskType.WORKFLOW, TaskType.DOWNLOAD):
            urls = self._get_urls(task_type)
            if not urls:
                QMessageBox.warning(
                    self, self.tr("错误"), self.tr("请输入至少一个 URL")
                )
                return

            for url in urls:
                params = self._collect_params(task_type, url)
                if params is not None:
                    self._task_mgr.create_task(task_type, params)
        else:
            params = self._collect_params(task_type)
            if params is None:
                QMessageBox.warning(
                    self, self.tr("错误"), self.tr("请填写所有必填字段")
                )
                return
            self._task_mgr.create_task(task_type, params)

        self.navigate_requested.emit("tasks")

    def _collect_params(self, task_type: TaskType, url: str = "") -> dict | None:
        """Collect parameters from the active form. Returns None if validation fails."""
        if task_type == TaskType.WORKFLOW:
            return {
                "url": url,
                "generate_transcript": self._wf_transcript.isChecked(),
                "target_language": self._wf_lang.currentData(),
            }

        if task_type == TaskType.DOWNLOAD:
            return {"url": url}

        if task_type == TaskType.TRANSLATE:
            path = self._tr_file.path()
            if not path:
                return None
            return {
                "subtitle_file": path,
                "target_language": self._tr_lang.currentData(),
            }

        if task_type == TaskType.SOFTSUB:
            video = self._ss_video.path()
            sub = self._ss_sub.path()
            if not video or not sub:
                return None
            params = {"video_file": video, "subtitle_file": sub}
            font = self._ss_font.path()
            if font:
                params["font_file"] = font
            return params

        if task_type == TaskType.HARDSUB:
            video = self._hs_video.path()
            sub = self._hs_sub.path()
            if not video or not sub:
                return None
            params = {"video_file": video, "subtitle_file": sub}
            font = self._hs_font.path()
            if font:
                params["font_file"] = font
            return params

        if task_type == TaskType.TRANSCRIPT:
            path = self._tc_file.path()
            if not path:
                return None
            return {"subtitle_file": path}

        if task_type == TaskType.FONT_SUBSET:
            sub = self._fs_sub.path()
            font = self._fs_font.path()
            if not sub or not font:
                return None
            return {"subtitle_file": sub, "font_file": font}

        return None

    def _on_task_double_clicked(self, _item: QListWidgetItem) -> None:
        self.navigate_requested.emit("tasks")

    def _on_task_progress(self, task_id: str, *_args: object) -> None:
        self._refresh_task_list()

    def _refresh_task_list(self, *_args: object) -> None:
        """Rebuild the active task list."""
        self._task_list.clear()
        if self._task_mgr is None:
            return
        for tid in reversed(self._task_mgr.task_order):
            task = self._task_mgr.get_task(tid)
            if task is None:
                continue
            # Assuming task has display_name and status_summary
            display_name = getattr(task, "display_name", tid)
            status_summary = getattr(task, "status_summary", "")
            item = QListWidgetItem(f"{display_name}   {status_summary}")
            item.setData(Qt.ItemDataRole.UserRole, tid)
            self._task_list.addItem(item)
