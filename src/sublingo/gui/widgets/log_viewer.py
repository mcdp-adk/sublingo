"""Log display widget with level filtering."""

from __future__ import annotations

from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import QTextEdit, QWidget


class LogViewer(QTextEdit):
    """Read-only text area for logs, colored by level."""

    def __init__(
        self, parent: QWidget | None = None, *, debug_mode: bool = False
    ) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self._debug_mode = debug_mode
        self._entries: list[tuple[str, str, str]] = []
        self._max_entries = 1000

    def set_debug_mode(self, enabled: bool) -> None:
        self._debug_mode = enabled
        self._rerender()

    @staticmethod
    def _log_color(level: str) -> str:
        upper = level.upper()
        if upper == "ERROR":
            return "#E06C75"
        if upper == "WARNING":
            return "#E5C07B"
        if upper == "OK" or upper == "INFO":
            return "#98C379" if upper == "OK" else ""
        return ""

    def append_log(self, level: str, message: str, detail: str = "") -> None:
        self._entries.append((level, message, detail))
        if len(self._entries) > self._max_entries:
            self._entries.pop(0)
        self._render_entry(level, message, detail)

    def _render_entry(self, level: str, message: str, detail: str = "") -> None:
        if level.upper() == "DEBUG" and not self._debug_mode:
            return

        fmt = QTextCharFormat()
        color = self._log_color(level)
        if color:
            fmt.setForeground(QColor(color))

        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(f"[{level.upper()}] {message}\n", fmt)

        if detail and self._debug_mode:
            detail_fmt = QTextCharFormat()
            detail_fmt.setForeground(QColor("#7f848e"))
            font = detail_fmt.font()
            font.setPointSizeF(font.pointSizeF() * 0.85)
            detail_fmt.setFont(font)
            cursor.insertText(f"  {detail}\n", detail_fmt)

        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def clear_logs(self) -> None:
        self._entries.clear()
        self.clear()

    def _rerender(self) -> None:
        self.clear()
        for level, message, detail in self._entries:
            self._render_entry(level, message, detail)
