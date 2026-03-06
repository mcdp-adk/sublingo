from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLabel, QVBoxLayout, QWidget, QWizardPage

from sublingo.gui.config_options import format_language_option_label
from sublingo.gui.config_options import GUI_LANGUAGES
from sublingo.gui.config_options import TARGET_LANGUAGES


class LanguagePage(QWizardPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle(self.tr("Language Settings"))
        self.setSubTitle(
            self.tr("Choose the interface language and target translation language.")
        )

        layout = QVBoxLayout(self)
        self._gui_lang_label = QLabel(self.tr("Interface Language:"))
        layout.addWidget(self._gui_lang_label)

        self.gui_language = QComboBox()
        for code, name in GUI_LANGUAGES.items():
            label = format_language_option_label(code, name, self.tr)
            self.gui_language.addItem(label, code)
        layout.addWidget(self.gui_language)

        self._target_label = QLabel(self.tr("Target Language:"))
        layout.addWidget(self._target_label)

        self.target_language = QComboBox()
        for code, name in TARGET_LANGUAGES.items():
            self.target_language.addItem(
                format_language_option_label(code, name, self.tr),
                code,
            )
        layout.addWidget(self.target_language)

        self._set_default_language(self.gui_language, "auto")
        self._set_default_language(self.target_language, "auto")
        layout.addStretch(1)

    def retranslateUi(self) -> None:
        self.setTitle(self.tr("Language Settings"))
        self.setSubTitle(
            self.tr("Choose the interface language and target translation language.")
        )
        self._gui_lang_label.setText(self.tr("Interface Language:"))
        self._target_label.setText(self.tr("Target Language:"))

    def _set_default_language(
        self, combo: QComboBox, language: str, *, fallback: str | None = None
    ) -> None:
        index = combo.findData(language)
        if index < 0 and fallback is not None:
            index = combo.findData(fallback)
        if index >= 0:
            combo.setCurrentIndex(index)
