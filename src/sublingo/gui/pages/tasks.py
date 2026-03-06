from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class TasksPage(QWidget):
    """Placeholder for the Tasks page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        title = QLabel(self.tr("Tasks"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
