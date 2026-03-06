from __future__ import annotations

from PySide6.QtWidgets import QTextEdit


class UrlInput(QTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setPlaceholderText(
            self.tr("Enter a video URL or YouTube playlist URL (one per line)")
        )
        self.setMaximumHeight(80)

    def urls(self) -> list[str]:
        return [
            line.strip() for line in self.toPlainText().splitlines() if line.strip()
        ]
