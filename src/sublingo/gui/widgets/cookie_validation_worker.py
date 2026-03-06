from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal


class CookieValidationWorker(QThread):
    result_ready = Signal(bool, str)

    def __init__(
        self,
        cookie_file: Path,
        proxy: str | None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._cookie_file = cookie_file
        self._proxy = proxy

    def run(self) -> None:
        try:
            from sublingo.core.cookie import validate_cookie_with_ytdlp

            success, message = validate_cookie_with_ytdlp(
                self._cookie_file,
                proxy=self._proxy,
            )
            self.result_ready.emit(success, message)
        except Exception as exc:
            self.result_ready.emit(False, str(exc))
