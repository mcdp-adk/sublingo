from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QWidget,
)

from sublingo.core.config import PROXY_MODE_CUSTOM
from sublingo.core.config import PROXY_MODE_DISABLED
from sublingo.core.config import PROXY_MODE_SYSTEM
from sublingo.core.config import SUBTITLE_MODE_HARD
from sublingo.core.config import SUBTITLE_MODE_SOFT
from sublingo.gui.config_options import format_language_option_label
from sublingo.gui.config_options import format_proxy_mode_label
from sublingo.gui.config_options import format_subtitle_mode_label
from sublingo.gui.config_options import GUI_LANGUAGES
from sublingo.gui.config_options import TARGET_LANGUAGES
from sublingo.gui.widgets.file_picker import FilePicker
from sublingo.gui.widgets.settings_section import SettingsSection

RowBuilder = Callable[[str, QWidget, str], QWidget]


def scan_font_files(project_root: Path) -> list[str]:
    fonts_dir = project_root / "fonts"
    if not fonts_dir.is_dir():
        return ["LXGWWenKai-Medium.ttf"]
    return sorted(path.name for path in fonts_dir.glob("*.ttf"))


class GUISettingsWidget(SettingsSection):
    def __init__(self, row_builder: RowBuilder, parent: QWidget | None = None) -> None:
        super().__init__(self.tr("GUI"), parent)
        self.gui_language = QComboBox()
        for code, name in GUI_LANGUAGES.items():
            label = format_language_option_label(code, name, self.tr)
            self.gui_language.addItem(label, code)
        self.add_row(
            row_builder(self.tr("Interface Language:"), self.gui_language, "language")
        )


class TranslationSettingsWidget(SettingsSection):
    def __init__(
        self,
        row_builder: RowBuilder,
        project_root: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(self.tr("Translation"), parent)
        self.target_language = QComboBox()
        for code, name in TARGET_LANGUAGES.items():
            self.target_language.addItem(
                format_language_option_label(code, name, self.tr),
                code,
            )
        self.add_row(
            row_builder(
                self.tr("Target Language:"), self.target_language, "target_language"
            )
        )

        self.font_file = QComboBox()
        for font_name in scan_font_files(project_root):
            self.font_file.addItem(font_name, font_name)
        self.add_row(row_builder(self.tr("Font File:"), self.font_file, "font_file"))

        self.generate_transcript = QCheckBox(
            self.tr("Generate transcript in workflows")
        )
        self.add_row(row_builder("", self.generate_transcript, "generate_transcript"))

        self.subtitle_mode = QComboBox()
        for mode in (SUBTITLE_MODE_SOFT, SUBTITLE_MODE_HARD):
            self.subtitle_mode.addItem(format_subtitle_mode_label(mode), mode)
        self.add_row(
            row_builder(
                self.tr("Subtitle Mode:"),
                self.subtitle_mode,
                "subtitle_mode",
            )
        )


class CookieSettingsWidget(SettingsSection):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(self.tr("Cookie"), parent)
        self.cookie_status = QLabel()
        self.section_layout.addWidget(self.cookie_status)

        self.cookie_input = QTextEdit()
        self.cookie_input.setPlaceholderText(self.tr("Paste Netscape cookie text here"))
        self.cookie_input.setMinimumHeight(76)
        self.section_layout.addWidget(self.cookie_input)

        button_row = QHBoxLayout()
        self.cookie_import_btn = QPushButton(self.tr("Import & Validate"))
        button_row.addWidget(self.cookie_import_btn)
        self.section_layout.addLayout(button_row)


class OutputSettingsWidget(SettingsSection):
    def __init__(self, row_builder: RowBuilder, parent: QWidget | None = None) -> None:
        super().__init__(self.tr("Output Paths"), parent)
        self.project_dir = FilePicker(mode="directory")
        self.add_row(
            row_builder(
                self.tr("Project Workspace Directory:"), self.project_dir, "project_dir"
            )
        )
        self.output_dir = FilePicker(mode="directory")
        self.add_row(
            row_builder(
                self.tr("Final Output Directory:"), self.output_dir, "output_dir"
            )
        )


class ProxySettingsWidget(SettingsSection):
    def __init__(self, row_builder: RowBuilder, parent: QWidget | None = None) -> None:
        super().__init__(self.tr("Proxy"), parent)
        self.proxy_mode = QComboBox()
        for mode in (PROXY_MODE_SYSTEM, PROXY_MODE_CUSTOM, PROXY_MODE_DISABLED):
            self.proxy_mode.addItem(format_proxy_mode_label(mode), mode)
        self.add_row(row_builder(self.tr("Proxy Mode:"), self.proxy_mode, "proxy_mode"))

        self.proxy = QLineEdit()
        self.proxy.setPlaceholderText("http://127.0.0.1:7890")
        self.add_row(row_builder(self.tr("Proxy URL:"), self.proxy, "proxy"))
        self.proxy_mode.currentIndexChanged.connect(self._sync_proxy_enabled_state)
        self._sync_proxy_enabled_state()

    def _sync_proxy_enabled_state(self) -> None:
        is_custom = self.proxy_mode.currentData() == PROXY_MODE_CUSTOM
        self.proxy.setEnabled(bool(is_custom))


class MaintenanceSettingsWidget(SettingsSection):
    def __init__(self, row_builder: RowBuilder, parent: QWidget | None = None) -> None:
        super().__init__(self.tr("Maintenance"), parent)
        self.debug_mode = QCheckBox(self.tr("Enable debug mode (show verbose logs)"))
        self.add_row(row_builder("", self.debug_mode, "debug_mode"))

        button_row = QHBoxLayout()
        self.reset_all_btn = QPushButton(self.tr("Reset All Settings"))
        button_row.addWidget(self.reset_all_btn)
        button_row.addStretch(1)
        self.section_layout.addLayout(button_row)
