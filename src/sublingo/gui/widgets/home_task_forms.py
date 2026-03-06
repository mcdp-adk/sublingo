from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QCheckBox, QComboBox, QSizePolicy, QVBoxLayout, QWidget

from sublingo.core.config import ConfigManager
from sublingo.gui.config_options import TARGET_LANGUAGES
from sublingo.gui.models.task_types import TaskType
from sublingo.gui.widgets.file_picker import FilePicker
from sublingo.gui.widgets.form_row import FormRow
from sublingo.gui.widgets.url_input import UrlInput


class HomeTaskForms(QWidget):
    def __init__(
        self, config_mgr: ConfigManager, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._config_mgr = config_mgr

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        from PySide6.QtWidgets import QStackedWidget

        self.form_stack = QStackedWidget()
        self.form_stack.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Maximum,
        )

        self.workflow_form = self._build_workflow_form()
        self.download_form = self._build_download_form()
        self.translate_form = self._build_translate_form()
        self.softsub_form = self._build_softsub_form()
        self.hardsub_form = self._build_hardsub_form()
        self.transcript_form = self._build_transcript_form()
        self.font_subset_form = self._build_font_subset_form()

        for form in (
            self.workflow_form,
            self.download_form,
            self.translate_form,
            self.softsub_form,
            self.hardsub_form,
            self.transcript_form,
            self.font_subset_form,
        ):
            self.form_stack.addWidget(form)

        layout.addWidget(self.form_stack)
        self.apply_config_defaults()

    def apply_config_defaults(self) -> None:
        cfg = self._config_mgr.config
        self.workflow_transcript.setChecked(cfg.generate_transcript)
        self._set_combo_by_data(self.workflow_language, cfg.target_language)
        self._set_combo_by_data(self.translate_language, cfg.target_language)

        font_path = self._config_mgr.project_root / "fonts" / cfg.font_file
        if font_path.exists():
            font_text = str(font_path)
            self.softsub_font.set_path(font_text)
            self.hardsub_font.set_path(font_text)
            self.font_subset_font.set_path(font_text)

    def set_current_index(self, index: int) -> None:
        self.form_stack.setCurrentIndex(index)

    def get_urls(self, task_type: TaskType) -> list[str]:
        if task_type == TaskType.WORKFLOW:
            return self.workflow_url.urls()
        if task_type == TaskType.DOWNLOAD:
            return self.download_url.urls()
        return []

    def collect_params(self, task_type: TaskType, url: str = "") -> dict | None:
        if task_type == TaskType.WORKFLOW:
            return {
                "url": url,
                "generate_transcript": self.workflow_transcript.isChecked(),
                "target_language": self.workflow_language.currentData(),
            }
        if task_type == TaskType.DOWNLOAD:
            return {"url": url}
        if task_type == TaskType.TRANSLATE:
            if not (path := self.translate_file.path()):
                return None
            return {
                "subtitle_file": path,
                "target_language": self.translate_language.currentData(),
            }
        if task_type == TaskType.SOFTSUB:
            return self._collect_video_subtitle_font_params(
                self.softsub_video,
                self.softsub_subtitle,
                self.softsub_font,
            )
        if task_type == TaskType.HARDSUB:
            return self._collect_video_subtitle_font_params(
                self.hardsub_video,
                self.hardsub_subtitle,
                self.hardsub_font,
            )
        if task_type == TaskType.TRANSCRIPT:
            if not (path := self.transcript_file.path()):
                return None
            return {"subtitle_file": path}
        if task_type == TaskType.FONT_SUBSET:
            subtitle = self.font_subset_subtitle.path()
            font = self.font_subset_font.path()
            if not subtitle or not font:
                return None
            return {"subtitle_file": subtitle, "font_file": font}
        return None

    def _build_workflow_form(self) -> QWidget:
        widget = QWidget()
        layout = self._build_form_layout(widget)
        self.workflow_url = UrlInput()
        layout.addWidget(FormRow(self.tr("URL:"), self.workflow_url))
        self.workflow_language = self._build_language_combo()
        layout.addWidget(FormRow(self.tr("Target Language:"), self.workflow_language))
        self.workflow_transcript = QCheckBox(self.tr("Generate transcript"))
        layout.addWidget(FormRow("", self.workflow_transcript))
        return widget

    def _build_download_form(self) -> QWidget:
        widget = QWidget()
        layout = self._build_form_layout(widget)
        self.download_url = UrlInput()
        layout.addWidget(FormRow(self.tr("URL:"), self.download_url))
        return widget

    def _build_translate_form(self) -> QWidget:
        widget = QWidget()
        layout = self._build_form_layout(widget)
        self.translate_file = FilePicker(
            mode="file",
            filter=self.tr("Subtitles (*.srt *.vtt *.ass)"),
        )
        layout.addWidget(FormRow(self.tr("Subtitle File:"), self.translate_file))
        self.translate_language = self._build_language_combo()
        layout.addWidget(FormRow(self.tr("Target Language:"), self.translate_language))
        return widget

    def _build_softsub_form(self) -> QWidget:
        widget = QWidget()
        layout = self._build_form_layout(widget)
        self.softsub_video = self._build_video_picker()
        self.softsub_subtitle = self._build_subtitle_picker()
        self.softsub_font = self._build_font_picker()
        layout.addWidget(FormRow(self.tr("Video File:"), self.softsub_video))
        layout.addWidget(FormRow(self.tr("Subtitle File:"), self.softsub_subtitle))
        layout.addWidget(FormRow(self.tr("Font File (optional):"), self.softsub_font))
        return widget

    def _build_hardsub_form(self) -> QWidget:
        widget = QWidget()
        layout = self._build_form_layout(widget)
        self.hardsub_video = self._build_video_picker()
        self.hardsub_subtitle = self._build_subtitle_picker()
        self.hardsub_font = self._build_font_picker()
        layout.addWidget(FormRow(self.tr("Video File:"), self.hardsub_video))
        layout.addWidget(FormRow(self.tr("Subtitle File:"), self.hardsub_subtitle))
        layout.addWidget(FormRow(self.tr("Font File (optional):"), self.hardsub_font))
        return widget

    def _build_transcript_form(self) -> QWidget:
        widget = QWidget()
        layout = self._build_form_layout(widget)
        self.transcript_file = self._build_subtitle_picker()
        layout.addWidget(FormRow(self.tr("Subtitle File:"), self.transcript_file))
        return widget

    def _build_font_subset_form(self) -> QWidget:
        widget = QWidget()
        layout = self._build_form_layout(widget)
        self.font_subset_subtitle = self._build_subtitle_picker()
        self.font_subset_font = self._build_font_picker()
        layout.addWidget(FormRow(self.tr("Subtitle File:"), self.font_subset_subtitle))
        layout.addWidget(FormRow(self.tr("Font File:"), self.font_subset_font))
        return widget

    def _build_form_layout(self, widget: QWidget) -> QVBoxLayout:
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 4, 0, 0)
        return layout

    def _build_language_combo(self) -> QComboBox:
        combo = QComboBox()
        for code, name in TARGET_LANGUAGES.items():
            combo.addItem(f"{name} ({code})", code)
        return combo

    def _build_video_picker(self) -> FilePicker:
        return FilePicker(
            mode="file",
            filter=self.tr("Video (*.mp4 *.mkv *.webm *.mov *.avi)"),
        )

    def _build_subtitle_picker(self) -> FilePicker:
        return FilePicker(
            mode="file",
            filter=self.tr("Subtitles (*.srt *.vtt *.ass)"),
        )

    def _build_font_picker(self) -> FilePicker:
        return FilePicker(
            mode="file",
            filter=self.tr("Font (*.ttf *.otf *.woff *.woff2)"),
        )

    def _collect_video_subtitle_font_params(
        self,
        video_picker: FilePicker,
        subtitle_picker: FilePicker,
        font_picker: FilePicker,
    ) -> dict[str, str] | None:
        video = video_picker.path()
        subtitle = subtitle_picker.path()
        if not video or not subtitle:
            return None
        params = {"video_file": video, "subtitle_file": subtitle}
        if font := font_picker.path():
            params["font_file"] = font
        return params

    def _set_combo_by_data(self, combo: QComboBox, value: str) -> None:
        if (index := combo.findData(value)) >= 0:
            combo.setCurrentIndex(index)
