from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QWizardPage,
)

from sublingo.gui.config_options import AI_PROVIDER_PRESETS
from sublingo.gui.config_options import format_provider_label
from sublingo.gui.widgets.ai_settings_widget import TestConnectionWorker


class AIConfigPage(QWizardPage):
    def __init__(
        self,
        *,
        default_provider: str,
        default_base_url: str,
        default_model: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._workers: list[TestConnectionWorker] = []
        self._default_provider = default_provider
        self._default_base_url = default_base_url
        self._default_model = default_model
        self.setTitle(self.tr("AI Configuration"))
        self.setSubTitle(self.tr("Configure AI provider and API key."))

        layout = QVBoxLayout(self)
        self._provider_label = QLabel(self.tr("Provider:"))
        layout.addWidget(self._provider_label)

        self.ai_provider = QComboBox()
        for key in AI_PROVIDER_PRESETS:
            self.ai_provider.addItem(format_provider_label(key), key)
        self.ai_provider.currentIndexChanged.connect(self._on_provider_changed)
        layout.addWidget(self.ai_provider)

        self._base_url_label = QLabel(self.tr("Base URL:"))
        layout.addWidget(self._base_url_label)
        self.ai_base_url = QLineEdit()
        layout.addWidget(self.ai_base_url)

        self._model_label = QLabel(self.tr("Model:"))
        layout.addWidget(self._model_label)
        self.ai_model = QLineEdit()
        layout.addWidget(self.ai_model)

        self._api_key_label = QLabel(self.tr("API Key:"))
        layout.addWidget(self._api_key_label)
        self.ai_api_key = QLineEdit()
        self.ai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.ai_api_key)

        self.test_btn = QPushButton(self.tr("Test Connection"))
        self.test_btn.clicked.connect(self._on_test)
        button_row = QHBoxLayout()
        button_row.addWidget(self.test_btn)
        button_row.addStretch(1)
        layout.addLayout(button_row)
        layout.addStretch(1)

        default_index = self.ai_provider.findData(self._default_provider)
        if default_index >= 0:
            self.ai_provider.setCurrentIndex(default_index)
        else:
            custom_index = self.ai_provider.findData("custom")
            if custom_index >= 0:
                self.ai_provider.setCurrentIndex(custom_index)

        self._on_provider_changed(0)
        self.ai_base_url.setText(self._default_base_url)
        self.ai_model.setText(self._default_model)

    def retranslateUi(self) -> None:
        self.setTitle(self.tr("AI Configuration"))
        self.setSubTitle(self.tr("Configure AI provider and API key."))
        self._provider_label.setText(self.tr("Provider:"))
        self._base_url_label.setText(self.tr("Base URL:"))
        self._model_label.setText(self.tr("Model:"))
        self._api_key_label.setText(self.tr("API Key:"))
        self.test_btn.setText(self.tr("Test Connection"))

    def _on_provider_changed(self, _index: int) -> None:
        provider_key = self.ai_provider.currentData()
        if provider_key and provider_key != "custom":
            if preset := AI_PROVIDER_PRESETS.get(provider_key):
                base_url, model = preset
                self.ai_base_url.setText(base_url)
                self.ai_model.setText(model)

    def _on_test(self) -> None:
        self.test_btn.setEnabled(False)
        self.test_btn.setText(self.tr("Testing..."))
        worker = TestConnectionWorker(
            base_url=self.ai_base_url.text(),
            api_key=self.ai_api_key.text(),
            model=self.ai_model.text(),
            parent=self,
        )
        worker.finished.connect(self._on_test_result)
        self._workers.append(worker)
        worker.start()

    def _on_test_result(self, success: bool, message: str) -> None:
        self.test_btn.setEnabled(True)
        self.test_btn.setText(self.tr("Test Connection"))
        if success:
            QMessageBox.information(self, self.tr("Connection Successful"), message)
        else:
            QMessageBox.warning(self, self.tr("Connection Failed"), message)
