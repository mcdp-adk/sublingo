from __future__ import annotations

from typing import Any

from PySide6.QtCore import QCoreApplication

from sublingo.gui.i18n_utils import detect_system_language
from sublingo.gui.i18n_utils import load_translator


class _FakeLocale:
    def __init__(self, name: str) -> None:
        self._name = name

    def name(self) -> str:
        return self._name


def _patch_system_locale(monkeypatch: Any, locale_name: str) -> None:
    class _FakeQLocale:
        @staticmethod
        def system() -> _FakeLocale:
            return _FakeLocale(locale_name)

    monkeypatch.setattr("sublingo.gui.i18n_utils.QLocale", _FakeQLocale)


def _get_app() -> QCoreApplication:
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def test_detect_system_language_prefers_simplified_chinese(monkeypatch: Any) -> None:
    _patch_system_locale(monkeypatch, "zh_TW")

    assert detect_system_language() == "zh-Hans"


def test_detect_system_language_falls_back_to_english(monkeypatch: Any) -> None:
    _patch_system_locale(monkeypatch, "fr_FR")

    assert detect_system_language() == "en"


def test_load_translator_installs_simplified_chinese_translation() -> None:
    app = _get_app()

    translator = load_translator(app, "zh_CN")

    assert translator is not None
    assert QCoreApplication.translate("MainWindow", "Ready") == "就绪"
    app.removeTranslator(translator)


def test_load_translator_installs_english_identity_translation() -> None:
    app = _get_app()

    translator = load_translator(app, "en")

    assert translator is not None
    assert QCoreApplication.translate("MainWindow", "Settings") == "Settings"
    app.removeTranslator(translator)


def test_load_translator_returns_none_for_unsupported_language() -> None:
    app = _get_app()

    assert load_translator(app, "ja") is None
