from __future__ import annotations

from typing import Any, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMessageBox,
    QProgressDialog,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)

DIALOG_MIN_WIDTH: int = 460


def show_info_dialog(parent: QWidget, title: str, text: str) -> None:
    _show_message_dialog(parent, QMessageBox.Icon.Information, title, text)


def show_warning_dialog(parent: QWidget, title: str, text: str) -> None:
    _show_message_dialog(parent, QMessageBox.Icon.Warning, title, text)


def show_question_dialog(
    parent: QWidget,
    title: str,
    text: str,
    *,
    buttons: QMessageBox.StandardButton,
    default_button: QMessageBox.StandardButton,
) -> QMessageBox.StandardButton:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(buttons)
    box.setDefaultButton(default_button)
    _apply_message_box_min_width(box)
    return QMessageBox.StandardButton(box.exec())


def create_busy_dialog(parent: QWidget, title: str, label: str) -> QProgressDialog:
    dialog = QProgressDialog(label, "", 0, 0, parent)
    dialog.setWindowTitle(title)
    dialog.setCancelButton(None)
    dialog.setMinimumDuration(0)
    dialog.setAutoClose(False)
    dialog.setAutoReset(False)
    dialog.setMinimumWidth(DIALOG_MIN_WIDTH)
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    return dialog


def create_progress_dialog(
    parent: QWidget,
    title: str,
    label: str,
    cancel_text: str,
    minimum: int,
    maximum: int,
) -> QProgressDialog:
    dialog = QProgressDialog(label, cancel_text, minimum, maximum, parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(DIALOG_MIN_WIDTH)
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    return dialog


def _show_message_dialog(
    parent: QWidget,
    icon: QMessageBox.Icon,
    title: str,
    text: str,
) -> None:
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    _apply_message_box_min_width(box)
    box.exec()


def _apply_message_box_min_width(box: QMessageBox) -> None:
    box.setMinimumWidth(DIALOG_MIN_WIDTH)
    layout_obj = box.layout()
    if layout_obj is None:
        return
    layout = cast(Any, layout_obj)
    spacer = QSpacerItem(
        DIALOG_MIN_WIDTH,
        0,
        QSizePolicy.Policy.Minimum,
        QSizePolicy.Policy.Expanding,
    )
    layout.addItem(spacer, layout.rowCount(), 0, 1, layout.columnCount())
