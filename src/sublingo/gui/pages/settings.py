"""Settings page – all configuration fields with per-field reset buttons."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from sublingo.core.config import ConfigManager
from sublingo.core.cookie import validate_cookie_file, import_cookie_file
from sublingo.gui.widgets.file_picker import FilePicker
from sublingo.gui.widgets.form_row import FormRow

_GUI_LANGUAGES: dict[str, str] = {
    "auto": "Auto",
    "en": "English",
    "zh-Hans": "简体中文",
}

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

_AI_PROVIDER_PRESETS: dict[str, tuple[str, str]] = {
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "gemini-2.0-flash",
    ),
    "deepseek": ("https://api.deepseek.com/v1", "deepseek-chat"),
    "openrouter": ("https://openrouter.ai/api/v1", "openrouter/auto"),
    "custom": ("", ""),
}


def _scan_font_files() -> list[str]:
    fonts_dir = Path(__file__).resolve().parent.parent.parent.parent.parent / "fonts"
    if not fonts_dir.is_dir():
        return ["LXGWWenKai-Medium.ttf"]
    return sorted(p.name for p in fonts_dir.glob("*.ttf"))


class _TestConnectionWorker(QThread):
    finished = Signal(bool, str)

    def __init__(
        self, base_url: str, api_key: str, model: str, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._base_url = base_url
        self._api_key = api_key
        self._model = model

    def run(self) -> None:
        try:
            from sublingo.core.ai_client import AiClient

            async def _test() -> tuple[bool, str]:
                client = AiClient(
                    base_url=self._base_url,
                    api_key=self._api_key,
                    model=self._model,
                )
                try:
                    return await client.test_connection()
                finally:
                    await client.close()

            success, message = asyncio.run(_test())
            self.finished.emit(success, message)
        except Exception as exc:
            self.finished.emit(False, str(exc))


class SettingsPage(QWidget):
    debug_mode_changed = Signal(bool)

    def __init__(
        self, config_mgr: ConfigManager, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._config_mgr = config_mgr
        self._workers: list[QThread] = []
        self._reset_buttons: dict[str, QPushButton] = {}
        self._loading = False

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer_layout.addWidget(scroll)

        container = QWidget()
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(20, 20, 20, 10)
        self._layout.setSpacing(16)
        scroll.setWidget(container)

        self._build_gui_section()
        self._build_translation_section()
        self._build_cookie_section()
        self._build_output_section()
        self._build_ai_section()
        self._build_proxy_section()
        self._build_maintenance_section()

        self._layout.addStretch(1)
        self._load_from_config()

    def _build_gui_section(self) -> None:
        group = QGroupBox(self.tr("GUI"))
        layout = QVBoxLayout(group)
        self._gui_language = QComboBox()
        for code, name in _GUI_LANGUAGES.items():
            self._gui_language.addItem(
                f"{name}" if code == "auto" else f"{name} ({code})", code
            )
        layout.addWidget(
            self._field_row(self.tr("界面语言:"), self._gui_language, "language")
        )
        self._layout.addWidget(group)

    def _build_translation_section(self) -> None:
        group = QGroupBox(self.tr("翻译"))
        layout = QVBoxLayout(group)
        self._target_language = QComboBox()
        for code, name in _TARGET_LANGUAGES.items():
            self._target_language.addItem(f"{name} ({code})", code)
        layout.addWidget(
            self._field_row(
                self.tr("目标语言:"), self._target_language, "target_language"
            )
        )

        self._font_file = QComboBox()
        for font_name in _scan_font_files():
            self._font_file.addItem(font_name, font_name)
        layout.addWidget(
            self._field_row(self.tr("字体文件:"), self._font_file, "font_file")
        )

        self._generate_transcript = QCheckBox(self.tr("全流程时生成转录"))
        layout.addWidget(
            self._field_row("", self._generate_transcript, "generate_transcript")
        )
        self._layout.addWidget(group)

    def _build_cookie_section(self) -> None:
        group = QGroupBox(self.tr("Cookie"))
        layout = QVBoxLayout(group)
        self._cookie_status = QLabel()
        layout.addWidget(self._cookie_status)

        import_row = QHBoxLayout()
        self._cookie_import_picker = FilePicker(
            mode="file", filter=self.tr("Text Files (*.txt)")
        )
        import_row.addWidget(self._cookie_import_picker, stretch=1)
        self._cookie_import_btn = QPushButton(self.tr("导入"))
        self._cookie_import_btn.clicked.connect(self._on_import_cookie)
        import_row.addWidget(self._cookie_import_btn)

        self._cookie_validate_btn = QPushButton(self.tr("验证"))
        self._cookie_validate_btn.clicked.connect(self._on_validate_cookie)
        import_row.addWidget(self._cookie_validate_btn)
        layout.addLayout(import_row)

        self._update_cookie_status()
        self._layout.addWidget(group)

    def _build_output_section(self) -> None:
        group = QGroupBox(self.tr("输出路径"))
        layout = QVBoxLayout(group)
        self._project_dir = FilePicker(mode="directory")
        layout.addWidget(
            self._field_row(self.tr("项目工作目录:"), self._project_dir, "project_dir")
        )
        self._output_dir = FilePicker(mode="directory")
        layout.addWidget(
            self._field_row(self.tr("最终输出目录:"), self._output_dir, "output_dir")
        )
        self._layout.addWidget(group)

    def _build_ai_section(self) -> None:
        group = QGroupBox(self.tr("AI"))
        layout = QVBoxLayout(group)

        self._ai_provider = QComboBox()
        for key in _AI_PROVIDER_PRESETS:
            self._ai_provider.addItem(key.capitalize(), key)
        self._ai_provider.currentIndexChanged.connect(self._on_provider_changed)
        layout.addWidget(
            self._field_row(self.tr("Provider:"), self._ai_provider, "ai_provider")
        )

        self._ai_base_url = QLineEdit()
        layout.addWidget(
            self._field_row(self.tr("Base URL:"), self._ai_base_url, "ai_base_url")
        )

        self._ai_model = QLineEdit()
        layout.addWidget(self._field_row(self.tr("Model:"), self._ai_model, "ai_model"))

        self._ai_api_key = QLineEdit()
        self._ai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(
            self._field_row(self.tr("API Key:"), self._ai_api_key, "ai_api_key")
        )

        self._ai_segment_batch_size = QSpinBox()
        self._ai_segment_batch_size.setRange(1, 200)
        layout.addWidget(
            self._field_row(
                self.tr("断句批次:"),
                self._ai_segment_batch_size,
                "ai_segment_batch_size",
            )
        )

        self._ai_translate_batch_size = QSpinBox()
        self._ai_translate_batch_size.setRange(1, 200)
        layout.addWidget(
            self._field_row(
                self.tr("翻译批次:"),
                self._ai_translate_batch_size,
                "ai_translate_batch_size",
            )
        )

        self._ai_proofread_batch_size = QSpinBox()
        self._ai_proofread_batch_size.setRange(1, 200)
        layout.addWidget(
            self._field_row(
                self.tr("校对批次:"),
                self._ai_proofread_batch_size,
                "ai_proofread_batch_size",
            )
        )

        self._ai_max_retries = QSpinBox()
        self._ai_max_retries.setRange(0, 20)
        layout.addWidget(
            self._field_row(
                self.tr("最大重试:"), self._ai_max_retries, "ai_max_retries"
            )
        )

        self._test_conn_btn = QPushButton(self.tr("测试连接"))
        self._test_conn_btn.clicked.connect(self._on_test_connection)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self._test_conn_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        self._layout.addWidget(group)

    def _build_proxy_section(self) -> None:
        group = QGroupBox(self.tr("代理"))
        layout = QVBoxLayout(group)
        self._proxy = QLineEdit()
        self._proxy.setPlaceholderText("http://127.0.0.1:7890")
        layout.addWidget(self._field_row(self.tr("代理地址:"), self._proxy, "proxy"))
        self._layout.addWidget(group)

    def _build_maintenance_section(self) -> None:
        group = QGroupBox(self.tr("维护"))
        layout = QVBoxLayout(group)
        self._debug_mode = QCheckBox(self.tr("启用调试模式（显示详细日志）"))
        layout.addWidget(self._field_row("", self._debug_mode, "debug_mode"))

        btn_row = QHBoxLayout()
        self._reset_all_btn = QPushButton(self.tr("重置所有设置"))
        self._reset_all_btn.clicked.connect(self._on_reset_all)
        btn_row.addWidget(self._reset_all_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        self._layout.addWidget(group)

    def _field_row(self, label_text: str, widget: QWidget, config_key: str) -> FormRow:
        row = FormRow(label_text, widget)
        reset_btn = QPushButton("R")
        reset_btn.setFixedSize(28, 28)
        reset_btn.setToolTip(self.tr("重置为默认值"))
        reset_btn.clicked.connect(
            lambda checked=False, key=config_key: self._reset_field(key)
        )
        row.add_action_widget(reset_btn)

        self._reset_buttons[config_key] = reset_btn
        self._update_reset_visibility(config_key)
        self._connect_auto_save(widget, config_key)
        return row

    def _update_reset_visibility(self, config_key: str) -> None:
        btn = self._reset_buttons.get(config_key)
        if btn is None:
            return
        current = self._read_widget_value(config_key)
        default = self._config_mgr.get_default(config_key)
        btn.setVisible(current != default)

    def _connect_auto_save(self, widget: QWidget, config_key: str) -> None:
        if isinstance(widget, FilePicker):
            widget.path_changed.connect(
                lambda _val, key=config_key: self._save_field(key)
            )
            widget.path_changed.connect(
                lambda _val, key=config_key: self._update_reset_visibility(key)
            )
        elif isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(
                lambda _idx, key=config_key: self._save_field(key)
            )
            widget.currentIndexChanged.connect(
                lambda _idx, key=config_key: self._update_reset_visibility(key)
            )
        elif isinstance(widget, QLineEdit):
            widget.editingFinished.connect(lambda key=config_key: self._save_field(key))
            widget.textChanged.connect(
                lambda _text, key=config_key: self._update_reset_visibility(key)
            )
        elif isinstance(widget, QSpinBox):
            widget.valueChanged.connect(
                lambda _val, key=config_key: self._save_field(key)
            )
            widget.valueChanged.connect(
                lambda _val, key=config_key: self._update_reset_visibility(key)
            )
        elif isinstance(widget, QCheckBox):
            widget.stateChanged.connect(
                lambda _state, key=config_key: self._save_field(key)
            )
            widget.stateChanged.connect(
                lambda _state, key=config_key: self._update_reset_visibility(key)
            )

    def _load_from_config(self) -> None:
        self._loading = True
        cfg = self._config_mgr.config

        self._project_dir.set_path(cfg.project_dir)
        self._output_dir.set_path(cfg.output_dir)
        self._set_combo_by_data(self._target_language, cfg.target_language)
        self._set_combo_by_data(self._font_file, cfg.font_file)
        self._generate_transcript.setChecked(cfg.generate_transcript)
        self._set_combo_by_data(self._ai_provider, cfg.ai_provider)
        self._ai_base_url.setText(cfg.ai_base_url)
        self._ai_api_key.setText(cfg.ai_api_key)
        self._ai_model.setText(cfg.ai_model)
        self._ai_translate_batch_size.setValue(cfg.ai_translate_batch_size)
        self._ai_proofread_batch_size.setValue(cfg.ai_proofread_batch_size)
        self._ai_segment_batch_size.setValue(cfg.ai_segment_batch_size)
        self._ai_max_retries.setValue(cfg.ai_max_retries)
        self._proxy.setText(cfg.proxy)
        self._set_combo_by_data(self._gui_language, cfg.language)
        self._debug_mode.setChecked(cfg.debug_mode)

        for key in self._reset_buttons:
            self._update_reset_visibility(key)
        self._loading = False

    def _read_widget_value(self, config_key: str) -> Any:
        widget_map: dict[str, QWidget | None] = {
            "project_dir": getattr(self, "_project_dir", None),
            "output_dir": getattr(self, "_output_dir", None),
            "target_language": getattr(self, "_target_language", None),
            "font_file": getattr(self, "_font_file", None),
            "generate_transcript": getattr(self, "_generate_transcript", None),
            "ai_provider": getattr(self, "_ai_provider", None),
            "ai_base_url": getattr(self, "_ai_base_url", None),
            "ai_api_key": getattr(self, "_ai_api_key", None),
            "ai_model": getattr(self, "_ai_model", None),
            "ai_translate_batch_size": getattr(self, "_ai_translate_batch_size", None),
            "ai_proofread_batch_size": getattr(self, "_ai_proofread_batch_size", None),
            "ai_segment_batch_size": getattr(self, "_ai_segment_batch_size", None),
            "ai_max_retries": getattr(self, "_ai_max_retries", None),
            "proxy": getattr(self, "_proxy", None),
            "language": getattr(self, "_gui_language", None),
            "debug_mode": getattr(self, "_debug_mode", None),
        }
        w = widget_map.get(config_key)
        if w is None:
            return None
        if isinstance(w, FilePicker):
            return w.path()
        if isinstance(w, QComboBox):
            return w.currentData()
        if isinstance(w, QLineEdit):
            return w.text()
        if isinstance(w, QSpinBox):
            return w.value()
        if isinstance(w, QCheckBox):
            return w.isChecked()
        return None

    def _save_field(self, config_key: str) -> None:
        value = self._read_widget_value(config_key)
        if value is None:
            return
        cfg = self._config_mgr.config
        if hasattr(cfg, config_key):
            old_value = getattr(cfg, config_key)
            setattr(cfg, config_key, value)
            self._config_mgr.save(cfg)
            if config_key == "language" and value != old_value:
                QMessageBox.information(
                    self, self.tr("提示"), self.tr("界面语言已保存，重启应用后生效。")
                )
            if config_key == "debug_mode" and value != old_value:
                self.debug_mode_changed.emit(bool(value))

    def _reset_field(self, config_key: str) -> None:
        default = self._config_mgr.get_default(config_key)
        if default is None:
            return
        cfg = self._config_mgr.config
        setattr(cfg, config_key, default)
        self._config_mgr.save(cfg)
        self._set_widget_value(config_key, default)
        self._update_reset_visibility(config_key)

    def _set_widget_value(self, config_key: str, value: Any) -> None:
        widget_map: dict[str, QWidget] = {
            "project_dir": self._project_dir,
            "output_dir": self._output_dir,
            "target_language": self._target_language,
            "font_file": self._font_file,
            "generate_transcript": self._generate_transcript,
            "ai_provider": self._ai_provider,
            "ai_base_url": self._ai_base_url,
            "ai_api_key": self._ai_api_key,
            "ai_model": self._ai_model,
            "ai_translate_batch_size": self._ai_translate_batch_size,
            "ai_proofread_batch_size": self._ai_proofread_batch_size,
            "ai_segment_batch_size": self._ai_segment_batch_size,
            "ai_max_retries": self._ai_max_retries,
            "proxy": self._proxy,
            "language": self._gui_language,
            "debug_mode": self._debug_mode,
        }
        w = widget_map.get(config_key)
        if w is None:
            return
        if isinstance(w, FilePicker):
            w.set_path(str(value))
        elif isinstance(w, QComboBox):
            self._set_combo_by_data(w, value)
        elif isinstance(w, QLineEdit):
            w.setText(str(value))
        elif isinstance(w, QSpinBox):
            w.setValue(int(value))
        elif isinstance(w, QCheckBox):
            w.setChecked(bool(value))

    @staticmethod
    def _set_combo_by_data(combo: QComboBox, data: Any) -> None:
        idx = combo.findData(data)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _on_provider_changed(self, index: int) -> None:
        if self._loading:
            return
        provider_key = self._ai_provider.currentData()
        if provider_key and provider_key != "custom":
            preset = _AI_PROVIDER_PRESETS.get(provider_key)
            if preset:
                base_url, model = preset
                self._ai_base_url.setText(base_url)
                self._ai_model.setText(model)
                self._save_field("ai_base_url")
                self._save_field("ai_model")

    def _on_test_connection(self) -> None:
        self._test_conn_btn.setEnabled(False)
        self._test_conn_btn.setText(self.tr("测试中…"))
        worker = _TestConnectionWorker(
            base_url=self._ai_base_url.text(),
            api_key=self._ai_api_key.text(),
            model=self._ai_model.text(),
            parent=self,
        )
        worker.finished.connect(self._on_test_connection_result)
        self._workers.append(worker)
        worker.start()

    def _on_test_connection_result(self, success: bool, message: str) -> None:
        self._test_conn_btn.setEnabled(True)
        self._test_conn_btn.setText(self.tr("测试连接"))
        if success:
            QMessageBox.information(self, self.tr("连接成功"), message)
        else:
            QMessageBox.warning(self, self.tr("连接失败"), message)

    def _on_import_cookie(self) -> None:
        source = self._cookie_import_picker.path().strip()
        if not source:
            return
        source_path = Path(source)
        if not source_path.exists():
            return
        import_cookie_file(source_path, self._config_mgr.cookie_file)
        self._update_cookie_status()
        QMessageBox.information(self, self.tr("导入成功"), self.tr("Cookie 文件已更新"))

    def _on_validate_cookie(self) -> None:
        cookie = self._config_mgr.cookie_file
        ok, msg = validate_cookie_file(cookie)
        if ok:
            QMessageBox.information(self, self.tr("验证通过"), msg)
        else:
            QMessageBox.warning(self, self.tr("验证失败"), msg)
        self._update_cookie_status()

    def _update_cookie_status(self) -> None:
        cookie = self._config_mgr.cookie_file
        if not cookie.exists() or cookie.stat().st_size == 0:
            self._cookie_status.setText(self.tr("Cookie 状态: 未导入"))
            self._cookie_status.setStyleSheet("color: #E5C07B;")
            return
        ok, msg = validate_cookie_file(cookie)
        if ok:
            size = cookie.stat().st_size
            self._cookie_status.setText(
                self.tr("Cookie 状态: {} ({} 字节)").format(msg, size)
            )
            self._cookie_status.setStyleSheet("color: #98C379;")
        else:
            self._cookie_status.setText(self.tr("Cookie 状态: {}").format(msg))
            self._cookie_status.setStyleSheet("color: #E06C75;")

    def _on_reset_all(self) -> None:
        reply = QMessageBox.question(
            self,
            self.tr("确认重置"),
            self.tr("确定要重置所有设置吗？这将删除 config.json 并需要重启应用。"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._config_mgr.reset()
            QMessageBox.information(
                self,
                self.tr("已重置"),
                self.tr("设置已重置，请重启应用以生效。"),
            )
