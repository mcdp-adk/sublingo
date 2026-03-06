from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QWidget


class SettingsSection(QGroupBox):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        self.section_layout = QVBoxLayout(self)

    def add_row(self, row: QWidget) -> None:
        self.section_layout.addWidget(row)
