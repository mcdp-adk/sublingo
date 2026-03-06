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
    QWidget,
)

from sublingo.gui.config_options import format_language_option_label
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
        super().__init__("GUI", parent)
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
            row_builder(self.tr("目标语言:"), self.target_language, "target_language")
        )

        self.font_file = QComboBox()
        for font_name in scan_font_files(project_root):
            self.font_file.addItem(font_name, font_name)
        self.add_row(row_builder(self.tr("字体文件:"), self.font_file, "font_file"))

        self.generate_transcript = QCheckBox(self.tr("全流程时生成转录"))
        self.add_row(row_builder("", self.generate_transcript, "generate_transcript"))


class CookieSettingsWidget(SettingsSection):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Cookie", parent)
        self.cookie_status = QLabel()
        self.section_layout.addWidget(self.cookie_status)

        button_row = QHBoxLayout()
        self.cookie_import_picker = FilePicker(
            mode="file",
            filter=self.tr("Text Files (*.txt)"),
        )
        button_row.addWidget(self.cookie_import_picker, stretch=1)
        self.cookie_import_btn = QPushButton(self.tr("导入"))
        button_row.addWidget(self.cookie_import_btn)
        self.cookie_validate_btn = QPushButton(self.tr("验证"))
        button_row.addWidget(self.cookie_validate_btn)
        self.section_layout.addLayout(button_row)


class OutputSettingsWidget(SettingsSection):
    def __init__(self, row_builder: RowBuilder, parent: QWidget | None = None) -> None:
        super().__init__(self.tr("Output Paths"), parent)
        self.project_dir = FilePicker(mode="directory")
        self.add_row(
            row_builder(self.tr("项目工作目录:"), self.project_dir, "project_dir")
        )
        self.output_dir = FilePicker(mode="directory")
        self.add_row(
            row_builder(self.tr("最终输出目录:"), self.output_dir, "output_dir")
        )


class ProxySettingsWidget(SettingsSection):
    def __init__(self, row_builder: RowBuilder, parent: QWidget | None = None) -> None:
        super().__init__(self.tr("Proxy"), parent)
        self.proxy = QLineEdit()
        self.proxy.setPlaceholderText("http://127.0.0.1:7890")
        self.add_row(row_builder(self.tr("代理地址:"), self.proxy, "proxy"))


class MaintenanceSettingsWidget(SettingsSection):
    def __init__(self, row_builder: RowBuilder, parent: QWidget | None = None) -> None:
        super().__init__(self.tr("Maintenance"), parent)
        self.debug_mode = QCheckBox(self.tr("启用调试模式（显示详细日志）"))
        self.add_row(row_builder("", self.debug_mode, "debug_mode"))

        button_row = QHBoxLayout()
        self.reset_all_btn = QPushButton(self.tr("重置所有设置"))
        button_row.addWidget(self.reset_all_btn)
        button_row.addStretch(1)
        self.section_layout.addLayout(button_row)
