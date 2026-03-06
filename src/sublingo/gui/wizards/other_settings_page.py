from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QWizardPage,
)

from sublingo.core.config import ConfigManager
from sublingo.core.cookie import (
    save_cookie_text,
    validate_cookie_file,
)
from sublingo.core.network_policy import resolve_download_proxy
from sublingo.gui.widgets.cookie_validation_worker import CookieValidationWorker
from sublingo.gui.widgets.dialogs import create_busy_dialog
from sublingo.gui.widgets.file_picker import FilePicker
from sublingo.gui.widgets.dialogs import show_info_dialog
from sublingo.gui.widgets.dialogs import show_warning_dialog


class OtherSettingsPage(QWizardPage):
    def __init__(
        self, config_mgr: ConfigManager, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._config_mgr = config_mgr
        self._workers: list[CookieValidationWorker] = []
        self._busy_dialog = None
        self.setTitle(self.tr("Other Settings"))
        self.setSubTitle(self.tr("Configure cookies and output directories."))

        layout = QVBoxLayout(self)
        self._cookie_label = QLabel(self.tr("Cookie Text (Netscape):"))
        layout.addWidget(self._cookie_label)

        self.cookie_input = QTextEdit()
        self.cookie_input.setPlaceholderText(self.tr("Paste Netscape cookie text here"))
        self.cookie_input.setMinimumHeight(76)
        layout.addWidget(self.cookie_input)

        cookie_row = QHBoxLayout()
        self.import_btn = QPushButton(self.tr("Import & Validate"))
        self.import_btn.clicked.connect(self._on_import)
        cookie_row.addWidget(self.import_btn)
        layout.addLayout(cookie_row)

        self.cookie_status = QLabel()
        layout.addWidget(self.cookie_status)
        self._update_cookie_status()

        self._project_output_label = QLabel(self.tr("Project Workspace Directory:"))
        layout.addWidget(self._project_output_label)
        self.project_dir = FilePicker(mode="directory")
        default_project_dir = self._config_mgr.get_default("project_dir")
        self.project_dir.set_path(str(default_project_dir or ""))
        layout.addWidget(self.project_dir)

        self._final_output_label = QLabel(self.tr("Final Output Directory:"))
        layout.addWidget(self._final_output_label)
        self.output_dir = FilePicker(mode="directory")
        default_output_dir = self._config_mgr.get_default("output_dir")
        self.output_dir.set_path(str(default_output_dir or ""))
        layout.addWidget(self.output_dir)

        layout.addStretch(1)

    def retranslateUi(self) -> None:
        self.setTitle(self.tr("Other Settings"))
        self.setSubTitle(self.tr("Configure cookies and output directories."))
        self._cookie_label.setText(self.tr("Cookie Text (Netscape):"))
        self.cookie_input.setPlaceholderText(self.tr("Paste Netscape cookie text here"))
        self.import_btn.setText(self.tr("Import & Validate"))
        self._project_output_label.setText(self.tr("Project Workspace Directory:"))
        self._final_output_label.setText(self.tr("Final Output Directory:"))
        self._update_cookie_status()

    def _on_import(self) -> None:
        cookie_file = self._config_mgr.cookie_file
        cookie_file.parent.mkdir(parents=True, exist_ok=True)
        if not cookie_file.exists():
            cookie_file.touch()

        ok, message = save_cookie_text(
            self.cookie_input.toPlainText(),
            cookie_file,
        )
        if not ok:
            show_warning_dialog(
                self,
                self.tr("Import Failed"),
                self.tr("{message}\n\nExpected format:\n{format_hint}").format(
                    message=self._localize_cookie_message(message),
                    format_hint=self.tr(
                        "Use tab separators (\\t): domain, include_subdomains, path, secure, expires, name, value"
                    ),
                ),
            )
            self._update_cookie_status()
            return
        self.import_btn.setEnabled(False)
        self.import_btn.setText(self.tr("Validating..."))
        self._show_busy(
            self.tr("Validating Cookie"),
            self.tr("Validating cookie with yt-dlp, please wait..."),
        )
        worker = CookieValidationWorker(
            cookie_file=cookie_file,
            proxy=resolve_download_proxy(self._config_mgr.config),
            parent=None,
        )
        worker.result_ready.connect(self._on_cookie_validation_result)
        self._register_worker(worker)
        self._set_wizard_nav_enabled(False)
        worker.start()

    def _on_cookie_validation_result(self, success: bool, message: str) -> None:
        self.import_btn.setEnabled(True)
        self.import_btn.setText(self.tr("Import & Validate"))
        self._hide_busy()
        self._set_wizard_nav_enabled(True)
        localized_message = self._localize_cookie_message(message)
        if success:
            show_info_dialog(
                self,
                self.tr("Import Successful"),
                self.tr(
                    "{message}\n\nCookie text saved to internal cookies.txt"
                ).format(message=localized_message),
            )
        else:
            show_warning_dialog(self, self.tr("Validation Failed"), localized_message)
        self._update_cookie_status()

    def _update_cookie_status(self) -> None:
        cookie = self._config_mgr.cookie_file
        if not cookie.exists() or cookie.stat().st_size == 0:
            self.cookie_status.setText(self.tr("Status: Not imported"))
            self.cookie_status.setStyleSheet("color: #E5C07B;")
            return
        ok, message = validate_cookie_file(cookie)
        localized_message = self._localize_cookie_message(message)
        if ok:
            self.cookie_status.setText(
                self.tr("Status: {} ({} bytes)").format(
                    localized_message, cookie.stat().st_size
                )
            )
            self.cookie_status.setStyleSheet("color: #98C379;")
        else:
            self.cookie_status.setText(self.tr("Status: {}").format(localized_message))
            self.cookie_status.setStyleSheet("color: #E06C75;")

    def _localize_cookie_message(self, message: str) -> str:
        message_map = {
            "Cookie file not found": self.tr("Cookie file not found"),
            "Cookie file is empty": self.tr("Cookie file is empty"),
            "Valid Netscape cookie format": self.tr("Valid Netscape cookie format"),
            "Invalid cookie format (expected Netscape)": self.tr(
                "Invalid cookie format (expected Netscape)"
            ),
            "Cookie content is empty": self.tr("Cookie content is empty"),
            "Cookie saved": self.tr("Cookie saved"),
            "Cookie validated with yt-dlp": self.tr("Cookie validated with yt-dlp"),
        }
        if message.startswith("yt-dlp validation failed: "):
            detail = message.split("yt-dlp validation failed: ", 1)[1]
            return self.tr("yt-dlp validation failed: {detail}").format(detail=detail)
        return message_map.get(message, message)

    def _show_busy(self, title: str, label: str) -> None:
        self._hide_busy()
        dialog = create_busy_dialog(self, title, label)
        dialog.show()
        self._busy_dialog = dialog

    def _hide_busy(self) -> None:
        if self._busy_dialog is None:
            return
        self._busy_dialog.close()
        self._busy_dialog.deleteLater()
        self._busy_dialog = None

    def _register_worker(self, worker: CookieValidationWorker) -> None:
        self._workers.append(worker)
        worker.result_ready.connect(lambda *_: self._finalize_worker(worker))

    def _finalize_worker(self, worker: CookieValidationWorker) -> None:
        if worker in self._workers:
            self._workers.remove(worker)
        worker.deleteLater()

    def _set_wizard_nav_enabled(self, enabled: bool) -> None:
        wizard = self.wizard()
        if wizard is None:
            return
        for button in (
            wizard.WizardButton.BackButton,
            wizard.WizardButton.NextButton,
            wizard.WizardButton.FinishButton,
            wizard.WizardButton.CancelButton,
        ):
            if btn := wizard.button(button):
                btn.setEnabled(enabled)
