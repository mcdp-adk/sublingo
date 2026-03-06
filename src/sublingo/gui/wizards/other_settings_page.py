from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QWizardPage,
)

from sublingo.core.config import ConfigManager
from sublingo.core.cookie import import_cookie_file, validate_cookie_file
from sublingo.gui.widgets.file_picker import FilePicker


class OtherSettingsPage(QWizardPage):
    def __init__(
        self, config_mgr: ConfigManager, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._config_mgr = config_mgr
        self.setTitle(self.tr("Other Settings"))
        self.setSubTitle(self.tr("Configure cookies, output directory, and proxy."))

        layout = QVBoxLayout(self)
        self._cookie_label = QLabel(self.tr("Cookie File:"))
        layout.addWidget(self._cookie_label)

        cookie_row = QHBoxLayout()
        self.cookie_picker = FilePicker(
            mode="file", filter=self.tr("Text Files (*.txt)")
        )
        cookie_row.addWidget(self.cookie_picker, stretch=1)
        self.import_btn = QPushButton(self.tr("Import"))
        self.import_btn.clicked.connect(self._on_import)
        cookie_row.addWidget(self.import_btn)
        self.validate_btn = QPushButton(self.tr("Validate"))
        self.validate_btn.clicked.connect(self._on_validate)
        cookie_row.addWidget(self.validate_btn)
        layout.addLayout(cookie_row)

        self.cookie_status = QLabel()
        layout.addWidget(self.cookie_status)
        self._update_cookie_status()

        self._output_label = QLabel(self.tr("Output Directory:"))
        layout.addWidget(self._output_label)
        self.output_dir = FilePicker(mode="directory")
        default_output_dir = self._config_mgr.get_default("output_dir")
        self.output_dir.set_path(str(default_output_dir or ""))
        layout.addWidget(self.output_dir)

        self._proxy_label = QLabel(self.tr("Proxy:"))
        layout.addWidget(self._proxy_label)
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("socks5://127.0.0.1:1080")
        layout.addWidget(self.proxy_input)
        layout.addStretch(1)

    def retranslateUi(self) -> None:
        self.setTitle(self.tr("Other Settings"))
        self.setSubTitle(self.tr("Configure cookies, output directory, and proxy."))
        self._cookie_label.setText(self.tr("Cookie File:"))
        self.import_btn.setText(self.tr("Import"))
        self.validate_btn.setText(self.tr("Validate"))
        self._output_label.setText(self.tr("Output Directory:"))
        self._proxy_label.setText(self.tr("Proxy:"))
        self._update_cookie_status()

    def _on_import(self) -> None:
        source = self.cookie_picker.path().strip()
        if not source:
            return
        source_path = Path(source)
        if not source_path.exists():
            return
        import_cookie_file(source_path, self._config_mgr.cookie_file)
        self._update_cookie_status()
        QMessageBox.information(
            self, self.tr("Import Successful"), self.tr("Cookie file imported.")
        )

    def _on_validate(self) -> None:
        ok, message = validate_cookie_file(self._config_mgr.cookie_file)
        if ok:
            QMessageBox.information(self, self.tr("Validation Passed"), message)
        else:
            QMessageBox.warning(self, self.tr("Validation Failed"), message)
        self._update_cookie_status()

    def _update_cookie_status(self) -> None:
        cookie = self._config_mgr.cookie_file
        if not cookie.exists() or cookie.stat().st_size == 0:
            self.cookie_status.setText(self.tr("Status: Not imported"))
            self.cookie_status.setStyleSheet("color: #E5C07B;")
            return
        ok, message = validate_cookie_file(cookie)
        if ok:
            self.cookie_status.setText(
                self.tr("Status: {} ({} bytes)").format(message, cookie.stat().st_size)
            )
            self.cookie_status.setStyleSheet("color: #98C379;")
        else:
            self.cookie_status.setText(self.tr("Status: {}").format(message))
            self.cookie_status.setStyleSheet("color: #E06C75;")
