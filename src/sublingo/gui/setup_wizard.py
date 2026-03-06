from __future__ import annotations

from PySide6.QtWidgets import QApplication, QWidget, QWizard

from sublingo.core.config import ConfigManager
from sublingo.core.cookie import validate_cookie_file
from sublingo.gui.i18n_utils import load_translator
from sublingo.gui.wizards.ai_config_page import AIConfigPage
from sublingo.gui.wizards.language_page import LanguagePage
from sublingo.gui.wizards.other_settings_page import OtherSettingsPage


class SetupWizard(QWizard):
    def __init__(
        self, config_mgr: ConfigManager, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._config_mgr = config_mgr
        self._translator = None

        self.setWindowTitle(self.tr("Sublingo Setup Wizard"))
        self.setMinimumSize(600, 450)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        self.lang_page = LanguagePage()
        self.ai_page = AIConfigPage(
            default_provider=self._config_mgr.get_default("ai_provider") or "custom",
            default_base_url=self._config_mgr.get_default("ai_base_url") or "",
            default_model=self._config_mgr.get_default("ai_model") or "",
        )
        self.other_page = OtherSettingsPage(config_mgr)

        self.addPage(self.lang_page)
        self.addPage(self.ai_page)
        self.addPage(self.other_page)

        self.lang_page.gui_language.currentIndexChanged.connect(
            self._on_language_changed
        )

    def _on_language_changed(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        if self._translator is not None:
            app.removeTranslator(self._translator)
            self._translator = None

        if lang_code := self.lang_page.gui_language.currentData():
            self._translator = load_translator(app, lang_code)
        self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(self.tr("Sublingo Setup Wizard"))
        self.lang_page.retranslateUi()
        self.ai_page.retranslateUi()
        self.other_page.retranslateUi()
        self.setButtonText(QWizard.WizardButton.BackButton, self.tr("< Back"))
        self.setButtonText(QWizard.WizardButton.NextButton, self.tr("Next >"))
        self.setButtonText(QWizard.WizardButton.FinishButton, self.tr("Finish"))
        self.setButtonText(QWizard.WizardButton.CancelButton, self.tr("Cancel"))

    def accept(self) -> None:
        cfg = self._config_mgr.config
        cfg.language = self.lang_page.gui_language.currentData()
        cfg.target_language = self.lang_page.target_language.currentData()
        cfg.ai_provider = self.ai_page.ai_provider.currentData()
        cfg.ai_base_url = self.ai_page.ai_base_url.text()
        cfg.ai_api_key = self.ai_page.ai_api_key.text()
        cfg.ai_model = self.ai_page.ai_model.text()
        cfg.output_dir = self.other_page.output_dir.path() or cfg.output_dir
        cfg.proxy = self.other_page.proxy_input.text()
        self._config_mgr.save(cfg)
        super().accept()
