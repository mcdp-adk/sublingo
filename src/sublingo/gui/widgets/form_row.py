"""Reusable form row component."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class FormRow(QWidget):
    """A reusable form row component with a label and a widget."""

    def __init__(
        self,
        label_text: str,
        widget: QWidget,
        parent: QWidget | None = None,
        label_min_width: int = 100,
    ) -> None:
        super().__init__(parent)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        if label_text:
            self._label = QLabel(label_text)
            self._label.setMinimumWidth(label_min_width)
            self._layout.addWidget(self._label)
        else:
            self._label = None

        self._layout.addWidget(widget, stretch=1)

    def add_action_widget(self, widget: QWidget) -> None:
        """Add an action widget (like a reset button) to the end of the row."""
        self._layout.addWidget(widget)

    def set_label_text(self, text: str) -> None:
        if self._label:
            self._label.setText(text)
