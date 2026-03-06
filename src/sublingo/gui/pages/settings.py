from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from sublingo.core.config import ConfigManager
from sublingo.core.cookie import import_cookie_file, validate_cookie_file
from sublingo.gui.config_options import AI_PROVIDER_PRESETS
from sublingo.gui.widgets.ai_settings_widget import AISettingsWidget
from sublingo.gui.widgets.ai_settings_widget import TestConnectionWorker
from sublingo.gui.widgets.file_picker import FilePicker
from sublingo.gui.widgets.form_row import FormRow
from sublingo.gui.widgets.settings_group_widgets import CookieSettingsWidget
from sublingo.gui.widgets.settings_group_widgets import GUISettingsWidget
from sublingo.gui.widgets.settings_group_widgets import MaintenanceSettingsWidget
from sublingo.gui.widgets.settings_group_widgets import OutputSettingsWidget
from sublingo.gui.widgets.settings_group_widgets import ProxySettingsWidget
from sublingo.gui.widgets.settings_group_widgets import TranslationSettingsWidget


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

        self._build_sections()
        self._layout.addStretch(1)
        self._load_from_config()

    def _build_sections(self) -> None:
        self._gui_section = GUISettingsWidget(self._field_row, self)
        self._translation_section = TranslationSettingsWidget(
            self._field_row,
            self._config_mgr.project_root,
            self,
        )
        self._cookie_section = CookieSettingsWidget(self)
        self._output_section = OutputSettingsWidget(self._field_row, self)
        self._ai_section = AISettingsWidget(self._field_row, self)
        self._proxy_section = ProxySettingsWidget(self._field_row, self)
        self._maintenance_section = MaintenanceSettingsWidget(self._field_row, self)

        self._cookie_section.cookie_import_btn.clicked.connect(self._on_import_cookie)
        self._cookie_section.cookie_validate_btn.clicked.connect(
            self._on_validate_cookie
        )
        self._ai_section.ai_provider.currentIndexChanged.connect(
            self._on_provider_changed
        )
        self._ai_section.test_conn_btn.clicked.connect(self._on_test_connection)
        self._maintenance_section.reset_all_btn.clicked.connect(self._on_reset_all)

        for section in (
            self._gui_section,
            self._translation_section,
            self._cookie_section,
            self._output_section,
            self._ai_section,
            self._proxy_section,
            self._maintenance_section,
        ):
            self._layout.addWidget(section)

        self._update_cookie_status()

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

    def _widget_map(self) -> dict[str, QWidget | None]:
        output_section = getattr(self, "_output_section", None)
        translation_section = getattr(self, "_translation_section", None)
        ai_section = getattr(self, "_ai_section", None)
        proxy_section = getattr(self, "_proxy_section", None)
        gui_section = getattr(self, "_gui_section", None)
        maintenance_section = getattr(self, "_maintenance_section", None)
        return {
            "project_dir": getattr(output_section, "project_dir", None),
            "output_dir": getattr(output_section, "output_dir", None),
            "target_language": getattr(translation_section, "target_language", None),
            "font_file": getattr(translation_section, "font_file", None),
            "generate_transcript": getattr(
                translation_section,
                "generate_transcript",
                None,
            ),
            "ai_provider": getattr(ai_section, "ai_provider", None),
            "ai_base_url": getattr(ai_section, "ai_base_url", None),
            "ai_api_key": getattr(ai_section, "ai_api_key", None),
            "ai_model": getattr(ai_section, "ai_model", None),
            "ai_translate_batch_size": getattr(
                ai_section,
                "ai_translate_batch_size",
                None,
            ),
            "ai_proofread_batch_size": getattr(
                ai_section,
                "ai_proofread_batch_size",
                None,
            ),
            "ai_segment_batch_size": getattr(
                ai_section,
                "ai_segment_batch_size",
                None,
            ),
            "ai_max_retries": getattr(ai_section, "ai_max_retries", None),
            "proxy": getattr(proxy_section, "proxy", None),
            "language": getattr(gui_section, "gui_language", None),
            "debug_mode": getattr(maintenance_section, "debug_mode", None),
        }

    def _read_widget_value(self, config_key: str) -> Any:
        widget = self._widget_map().get(config_key)
        if widget is None:
            return None
        if isinstance(widget, FilePicker):
            return widget.path()
        if isinstance(widget, QComboBox):
            return widget.currentData()
        if isinstance(widget, QLineEdit):
            return widget.text()
        if isinstance(widget, QSpinBox):
            return widget.value()
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        return None

    def _set_widget_value(self, config_key: str, value: Any) -> None:
        widget = self._widget_map().get(config_key)
        if widget is None:
            return
        if isinstance(widget, FilePicker):
            widget.set_path(str(value))
        elif isinstance(widget, QComboBox):
            self._set_combo_by_data(widget, value)
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value))
        elif isinstance(widget, QSpinBox):
            widget.setValue(int(value))
        elif isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))

    def _load_from_config(self) -> None:
        self._loading = True
        cfg = self._config_mgr.config
        values = {
            "project_dir": cfg.project_dir,
            "output_dir": cfg.output_dir,
            "target_language": cfg.target_language,
            "font_file": cfg.font_file,
            "generate_transcript": cfg.generate_transcript,
            "ai_provider": cfg.ai_provider,
            "ai_base_url": cfg.ai_base_url,
            "ai_api_key": cfg.ai_api_key,
            "ai_model": cfg.ai_model,
            "ai_translate_batch_size": cfg.ai_translate_batch_size,
            "ai_proofread_batch_size": cfg.ai_proofread_batch_size,
            "ai_segment_batch_size": cfg.ai_segment_batch_size,
            "ai_max_retries": cfg.ai_max_retries,
            "proxy": cfg.proxy,
            "language": cfg.language,
            "debug_mode": cfg.debug_mode,
        }
        for key, value in values.items():
            self._set_widget_value(key, value)
        for key in self._reset_buttons:
            self._update_reset_visibility(key)
        self._loading = False

    def _update_reset_visibility(self, config_key: str) -> None:
        if (button := self._reset_buttons.get(config_key)) is None:
            return
        button.setVisible(
            self._read_widget_value(config_key)
            != self._config_mgr.get_default(config_key)
        )

    def _save_field(self, config_key: str) -> None:
        value = self._read_widget_value(config_key)
        if value is None:
            return
        cfg = self._config_mgr.config
        if not hasattr(cfg, config_key):
            return
        old_value = getattr(cfg, config_key)
        setattr(cfg, config_key, value)
        self._config_mgr.save(cfg)
        if config_key == "language" and value != old_value:
            QMessageBox.information(
                self,
                self.tr("提示"),
                self.tr("界面语言已保存，重启应用后生效。"),
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

    @staticmethod
    def _set_combo_by_data(combo: QComboBox, value: Any) -> None:
        if (index := combo.findData(value)) >= 0:
            combo.setCurrentIndex(index)

    def _on_provider_changed(self, _index: int) -> None:
        if self._loading:
            return
        provider_key = self._ai_section.ai_provider.currentData()
        if provider_key and provider_key != "custom":
            if preset := AI_PROVIDER_PRESETS.get(provider_key):
                base_url, model = preset
                self._ai_section.ai_base_url.setText(base_url)
                self._ai_section.ai_model.setText(model)
                self._save_field("ai_base_url")
                self._save_field("ai_model")

    def _on_test_connection(self) -> None:
        self._ai_section.test_conn_btn.setEnabled(False)
        self._ai_section.test_conn_btn.setText(self.tr("测试中…"))
        worker = TestConnectionWorker(
            base_url=self._ai_section.ai_base_url.text(),
            api_key=self._ai_section.ai_api_key.text(),
            model=self._ai_section.ai_model.text(),
            parent=self,
        )
        worker.finished.connect(self._on_test_connection_result)
        self._workers.append(worker)
        worker.start()

    def _on_test_connection_result(self, success: bool, message: str) -> None:
        self._ai_section.test_conn_btn.setEnabled(True)
        self._ai_section.test_conn_btn.setText(self.tr("测试连接"))
        if success:
            QMessageBox.information(self, self.tr("连接成功"), message)
        else:
            QMessageBox.warning(self, self.tr("连接失败"), message)

    def _on_import_cookie(self) -> None:
        source = self._cookie_section.cookie_import_picker.path().strip()
        if not source:
            return
        import_cookie_file(Path(source), self._config_mgr.cookie_file)
        self._update_cookie_status()
        QMessageBox.information(self, self.tr("导入成功"), self.tr("Cookie 文件已更新"))

    def _on_validate_cookie(self) -> None:
        ok, message = validate_cookie_file(self._config_mgr.cookie_file)
        if ok:
            QMessageBox.information(self, self.tr("验证通过"), message)
        else:
            QMessageBox.warning(self, self.tr("验证失败"), message)
        self._update_cookie_status()

    def _update_cookie_status(self) -> None:
        cookie = self._config_mgr.cookie_file
        if not cookie.exists() or cookie.stat().st_size == 0:
            self._cookie_section.cookie_status.setText(self.tr("Cookie 状态: 未导入"))
            self._cookie_section.cookie_status.setStyleSheet("color: #E5C07B;")
            return
        ok, message = validate_cookie_file(cookie)
        if ok:
            self._cookie_section.cookie_status.setText(
                self.tr("Cookie 状态: {} ({} 字节)").format(
                    message, cookie.stat().st_size
                )
            )
            self._cookie_section.cookie_status.setStyleSheet("color: #98C379;")
        else:
            self._cookie_section.cookie_status.setText(
                self.tr("Cookie 状态: {}").format(message)
            )
            self._cookie_section.cookie_status.setStyleSheet("color: #E06C75;")

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
