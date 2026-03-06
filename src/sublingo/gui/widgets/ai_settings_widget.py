from __future__ import annotations

import asyncio
from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from sublingo.gui.config_options import AI_PROVIDER_PRESETS
from sublingo.gui.config_options import format_provider_label
from sublingo.gui.widgets.settings_section import SettingsSection


class TestConnectionWorker(QThread):
    finished = Signal(bool, str)

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        proxy: str | None,
        trust_env: bool,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._proxy = proxy
        self._trust_env = trust_env

    def run(self) -> None:
        try:
            from sublingo.core.ai_client import AiClient

            async def _test() -> tuple[bool, str]:
                client = AiClient(
                    base_url=self._base_url,
                    api_key=self._api_key,
                    model=self._model,
                    proxy=self._proxy,
                    trust_env=self._trust_env,
                )
                try:
                    return await client.test_connection()
                finally:
                    await client.close()

            success, message = asyncio.run(_test())
            self.finished.emit(success, message)
        except Exception as exc:
            self.finished.emit(False, str(exc))


class AISettingsWidget(SettingsSection):
    def __init__(
        self,
        row_builder: Callable[[str, QWidget, str], QWidget],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(self.tr("AI"), parent)
        self.ai_provider = QComboBox()
        for key in AI_PROVIDER_PRESETS:
            self.ai_provider.addItem(format_provider_label(key), key)
        self.add_row(row_builder(self.tr("Provider:"), self.ai_provider, "ai_provider"))

        self.ai_base_url = QLineEdit()
        self.add_row(row_builder(self.tr("Base URL:"), self.ai_base_url, "ai_base_url"))

        self.ai_model = QLineEdit()
        self.add_row(row_builder(self.tr("Model:"), self.ai_model, "ai_model"))

        self.ai_api_key = QLineEdit()
        self.ai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.add_row(row_builder(self.tr("API Key:"), self.ai_api_key, "ai_api_key"))

        self.ai_segment_batch_size = QSpinBox()
        self.ai_segment_batch_size.setRange(1, 200)
        self.add_row(
            row_builder(
                self.tr("Segmentation Batch Size:"),
                self.ai_segment_batch_size,
                "ai_segment_batch_size",
            )
        )

        self.ai_translate_batch_size = QSpinBox()
        self.ai_translate_batch_size.setRange(1, 200)
        self.add_row(
            row_builder(
                self.tr("Translation Batch Size:"),
                self.ai_translate_batch_size,
                "ai_translate_batch_size",
            )
        )

        self.ai_proofread_batch_size = QSpinBox()
        self.ai_proofread_batch_size.setRange(1, 200)
        self.add_row(
            row_builder(
                self.tr("Proofreading Batch Size:"),
                self.ai_proofread_batch_size,
                "ai_proofread_batch_size",
            )
        )

        self.ai_max_retries = QSpinBox()
        self.ai_max_retries.setRange(0, 20)
        self.add_row(
            row_builder(
                self.tr("Max Retries:"),
                self.ai_max_retries,
                "ai_max_retries",
            )
        )

        button_row = QHBoxLayout()
        self.test_conn_btn = QPushButton(self.tr("Test Connection"))
        button_row.addWidget(self.test_conn_btn)
        button_row.addStretch(1)
        self.section_layout.addLayout(button_row)
