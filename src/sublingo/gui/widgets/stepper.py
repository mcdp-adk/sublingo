"""Stepper widget -- visual stage pipeline with progress."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class Stepper(QWidget):
    """Multi-stage pipeline progress indicator using text symbols."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(10)
        self._stages: list[str] = []
        self._statuses: dict[str, str] = {}
        self._labels: dict[str, QLabel] = {}

    def set_stages(self, stages: list[str]) -> None:
        """Initialize stage list."""
        self._stages = list(stages)
        self._statuses = {s: "pending" for s in stages}

        # Clear layout
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._labels.clear()

        for i, stage in enumerate(self._stages):
            lbl = QLabel()
            self._layout.addWidget(lbl)
            self._labels[stage] = lbl

            if i < len(self._stages) - 1:
                arrow = QLabel("→")
                arrow.setStyleSheet("color: gray;")
                self._layout.addWidget(arrow)

        self._layout.addStretch()
        self._update_display()

    def set_stage_status(self, stage: str, status: str, percent: int = 0) -> None:
        """Update stage status."""
        if stage not in self._statuses:
            return
        self._statuses[stage] = status
        self._update_display()

    def _update_display(self) -> None:
        for stage in self._stages:
            status = self._statuses.get(stage, "pending")
            lbl = self._labels.get(stage)
            if not lbl:
                continue

            if status == "done":
                symbol = "✓"
                color = "#98C379"
            elif status == "active":
                symbol = "●"
                color = "#61AFEF"
            elif status == "error":
                symbol = "✗"
                color = "#E06C75"
            else:
                symbol = "○"
                color = "#5C6370"

            lbl.setText(f"{symbol} {stage}")
            lbl.setStyleSheet(f"color: {color}; font-weight: bold;")
