from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sublingo.core.downloader import extract_info, extract_playlist_info

PREVIEW_INCLUDE_COLUMN = 0
PREVIEW_TITLE_COLUMN = 1
PREVIEW_DURATION_COLUMN = 2
PREVIEW_SUBTITLE_COLUMN = 3


def format_duration(seconds: int) -> str:
    minutes, sec = divmod(max(seconds, 0), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{sec:02}"
    return f"{minutes:02}:{sec:02}"


def has_subtitles(video: Any) -> bool:
    subtitles = getattr(video, "available_subtitles", {}) or {}
    auto_captions = getattr(video, "available_auto_captions", {}) or {}
    return bool(subtitles or auto_captions)


def is_playlist_url(url: str) -> bool:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return "list" in query or "playlist" in parsed.path.lower()


@dataclass
class PreviewVideoRow:
    url: str
    title: str
    duration: int
    has_subtitles: bool


class PreviewFetchWorker(QThread):
    progress = Signal(int, int, str)
    result_ready = Signal(list)
    task_error = Signal(str)

    def __init__(
        self,
        urls: list[str],
        *,
        cookie_file: Path,
        proxy: str | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._urls = urls
        self._cookie_file = cookie_file
        self._proxy = proxy

    def run(self) -> None:
        rows: list[PreviewVideoRow] = []
        total = len(self._urls)
        try:
            for index, url in enumerate(self._urls, start=1):
                if self.isInterruptionRequested():
                    return
                self.progress.emit(index, total, url)
                rows.extend(self._rows_for_url(url))
        except Exception as exc:  # noqa: BLE001
            self.task_error.emit(str(exc))
            return

        self.result_ready.emit(rows)

    def _rows_for_url(self, url: str) -> list[PreviewVideoRow]:
        return [
            PreviewVideoRow(
                url=getattr(video, "url", "") or url,
                title=getattr(video, "title", ""),
                duration=int(getattr(video, "duration", 0) or 0),
                has_subtitles=has_subtitles(video),
            )
            for video in self._fetch_url(url)
            if not self.isInterruptionRequested()
        ]

    def _fetch_url(self, url: str) -> list[Any]:
        if is_playlist_url(url):
            return extract_playlist_info(
                url,
                cookie_file=self._cookie_file,
                proxy=self._proxy,
            )
        return [
            extract_info(
                url,
                cookie_file=self._cookie_file,
                proxy=self._proxy,
            )
        ]


class PreviewDialog(QDialog):
    def __init__(
        self, videos: list[PreviewVideoRow], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Batch Preview"))
        self.resize(760, 420)

        layout = QVBoxLayout(self)
        self._table = QTableWidget(len(videos), 4)
        self._table.setHorizontalHeaderLabels(
            [
                self.tr("Include"),
                self.tr("Title"),
                self.tr("Duration"),
                self.tr("Subtitles"),
            ]
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        for row_index, video in enumerate(videos):
            include_item = QTableWidgetItem()
            include_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            include_item.setCheckState(Qt.CheckState.Checked)
            include_item.setData(Qt.ItemDataRole.UserRole, video.url)
            self._table.setItem(row_index, PREVIEW_INCLUDE_COLUMN, include_item)
            self._table.setItem(
                row_index,
                PREVIEW_TITLE_COLUMN,
                QTableWidgetItem(video.title or self.tr("Untitled video")),
            )
            self._table.setItem(
                row_index,
                PREVIEW_DURATION_COLUMN,
                QTableWidgetItem(format_duration(video.duration)),
            )
            self._table.setItem(
                row_index,
                PREVIEW_SUBTITLE_COLUMN,
                QTableWidgetItem(
                    self.tr("Yes") if video.has_subtitles else self.tr("No")
                ),
            )

        header = self._table.horizontalHeader()
        header.setStretchLastSection(False)
        header.resizeSection(PREVIEW_INCLUDE_COLUMN, 64)
        header.resizeSection(PREVIEW_DURATION_COLUMN, 96)
        header.resizeSection(PREVIEW_SUBTITLE_COLUMN, 96)
        header.setSectionResizeMode(PREVIEW_TITLE_COLUMN, header.ResizeMode.Stretch)

        layout.addWidget(self._table)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_urls(self) -> list[str]:
        urls: list[str] = []
        for row in range(self._table.rowCount()):
            item = self._table.item(row, PREVIEW_INCLUDE_COLUMN)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                urls.append(str(item.data(Qt.ItemDataRole.UserRole) or ""))
        return [url for url in urls if url]
