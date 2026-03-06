from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLocale, QTranslator

AUTO_LANGUAGE = "auto"
DEFAULT_LANGUAGE = "en"
SIMPLIFIED_CHINESE = "zh-Hans"
LANGUAGE_FILE_MAP: dict[str, str] = {
    DEFAULT_LANGUAGE: "sublingo_en.qm",
    SIMPLIFIED_CHINESE: "sublingo_zh_Hans.qm",
}
I18N_DIR = Path(__file__).resolve().parent.parent / "i18n"


def load_translator(
    app: QCoreApplication, language: str = AUTO_LANGUAGE
) -> QTranslator | None:
    """Load and install the translator for a supported language."""
    resolved_language = (
        detect_system_language()
        if language == AUTO_LANGUAGE
        else _normalize_language_code(language)
    )
    if resolved_language is None:
        return None

    qm_name = LANGUAGE_FILE_MAP[resolved_language]
    qm_path = I18N_DIR / qm_name
    if not qm_path.exists():
        return None

    translator = QTranslator()
    if not translator.load(str(qm_path)):
        return None

    app.installTranslator(translator)
    return translator


def detect_system_language() -> str:
    """Return the nearest supported language for the active system locale."""
    locale_name = QLocale.system().name()
    return _normalize_language_code(locale_name) or DEFAULT_LANGUAGE


def _normalize_language_code(language: str) -> str | None:
    normalized = language.strip().replace("_", "-")
    if not normalized:
        return None

    lowered = normalized.casefold()
    if lowered == DEFAULT_LANGUAGE or lowered.startswith(f"{DEFAULT_LANGUAGE}-"):
        return DEFAULT_LANGUAGE

    # The app currently ships only Simplified Chinese, so all Chinese locales
    # resolve to the nearest supported translator.
    if lowered == "zh" or lowered.startswith("zh-"):
        return SIMPLIFIED_CHINESE

    return None
