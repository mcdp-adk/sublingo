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

from sublingo.core.config import PROXY_MODE_CUSTOM
from sublingo.core.config import PROXY_MODE_DISABLED
from sublingo.core.config import PROXY_MODE_SYSTEM
from sublingo.core.network_policy import resolve_http_proxy_from_values
from sublingo.gui.config_options import AI_PROVIDER_PRESETS
from sublingo.gui.config_options import format_provider_label
from sublingo.gui.config_options import format_proxy_mode_label
from sublingo.gui.widgets.ai_settings_widget import TestConnectionWorker


class AIConfigPage(QWizardPage):
    def __init__(
        self,
        *,
        default_provider: str,
        default_base_url: str,
        default_model: str,
        default_proxy_mode: str,
        default_proxy: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._workers: list[TestConnectionWorker] = []
        self._default_provider = default_provider
        self._default_base_url = default_base_url
        self._default_model = default_model
        self._default_proxy_mode = default_proxy_mode
        self._default_proxy = default_proxy
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

        self._proxy_mode_label = QLabel(self.tr("Proxy Mode:"))
        layout.addWidget(self._proxy_mode_label)
        self.proxy_mode = QComboBox()
        for mode in (PROXY_MODE_SYSTEM, PROXY_MODE_CUSTOM, PROXY_MODE_DISABLED):
            self.proxy_mode.addItem(format_proxy_mode_label(mode), mode)
        self.proxy_mode.currentIndexChanged.connect(self._sync_proxy_enabled_state)
        layout.addWidget(self.proxy_mode)

        self._proxy_url_label = QLabel(self.tr("Proxy URL:"))
        layout.addWidget(self._proxy_url_label)
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("http://127.0.0.1:7890")
        layout.addWidget(self.proxy_input)

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
        proxy_mode_index = self.proxy_mode.findData(self._default_proxy_mode)
        if proxy_mode_index >= 0:
            self.proxy_mode.setCurrentIndex(proxy_mode_index)
        self.proxy_input.setText(self._default_proxy)
        self._sync_proxy_enabled_state()

    def retranslateUi(self) -> None:
        self.setTitle(self.tr("AI Configuration"))
        self.setSubTitle(self.tr("Configure AI provider and API key."))
        self._provider_label.setText(self.tr("Provider:"))
        self._base_url_label.setText(self.tr("Base URL:"))
        self._model_label.setText(self.tr("Model:"))
        self._api_key_label.setText(self.tr("API Key:"))
        self._proxy_mode_label.setText(self.tr("Proxy Mode:"))
        self._proxy_url_label.setText(self.tr("Proxy URL:"))
        for index in range(self.proxy_mode.count()):
            mode = str(self.proxy_mode.itemData(index) or "")
            self.proxy_mode.setItemText(index, format_proxy_mode_label(mode))
        self.test_btn.setText(self.tr("Test Connection"))

    def _sync_proxy_enabled_state(self) -> None:
        self.proxy_input.setEnabled(self.proxy_mode.currentData() == PROXY_MODE_CUSTOM)

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
        policy = resolve_http_proxy_from_values(
            str(self.proxy_mode.currentData() or PROXY_MODE_SYSTEM),
            self.proxy_input.text(),
        )
        worker = TestConnectionWorker(
            base_url=self.ai_base_url.text(),
            api_key=self.ai_api_key.text(),
            model=self.ai_model.text(),
            proxy=policy.proxy,
            trust_env=policy.trust_env,
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
