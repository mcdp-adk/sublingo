from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)


class FilePicker(QWidget):
    """Text box + Browse button."""

    path_changed = Signal(str)

    def __init__(
        self,
        mode: str = "file",
        filter: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._filter = filter

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._line_edit = QLineEdit()
        self._line_edit.setPlaceholderText(
            self.tr("Select a file...")
            if mode == "file"
            else self.tr("Select a directory...")
        )
        self._line_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._line_edit, stretch=1)

        self._browse_btn = QPushButton(self.tr("Browse..."))
        self._browse_btn.clicked.connect(self._on_browse)
        layout.addWidget(self._browse_btn)

    def path(self) -> str:
        return self._line_edit.text()

    def set_path(self, path: str) -> None:
        self._line_edit.setText(path)

    def _on_text_changed(self, text: str) -> None:
        self.path_changed.emit(text)

    def _on_browse(self) -> None:
        if self._mode == "directory":
            path = QFileDialog.getExistingDirectory(
                self,
                self.tr("Select Directory"),
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self,
                self.tr("Select File"),
                "",
                self._filter,
            )

        if path:
            self._line_edit.setText(path)
