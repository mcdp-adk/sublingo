from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QCoreApplication

from sublingo.core.config import AI_PROVIDER_PRESETS
from sublingo.core.config import PROXY_MODE_CUSTOM
from sublingo.core.config import PROXY_MODE_DISABLED
from sublingo.core.config import PROXY_MODE_SYSTEM
from sublingo.core.config import SUBTITLE_MODE_HARD
from sublingo.core.config import SUBTITLE_MODE_SOFT


PROVIDER_DISPLAY_NAMES: dict[str, str] = {
    "openai": "OpenAI",
    "deepseek": "DeepSeek",
    "openrouter": "OpenRouter",
}


def format_provider_label(provider_key: str) -> str:
    return PROVIDER_DISPLAY_NAMES.get(provider_key, provider_key.capitalize())


def format_language_option_label(
    code: str,
    name: str,
    translator: Callable[[str], str] | None = None,
) -> str:
    if code == "auto":
        return QCoreApplication.translate("LanguageOption", "System Language")
    return f"{name} ({code})"


GUI_LANGUAGES: dict[str, str] = {
    "auto": "System Language",
    "en": "English",
    "zh-Hans": "简体中文",
}

TARGET_LANGUAGES: dict[str, str] = {
    "auto": "System Language",
    "zh-Hans": "简体中文",
    "zh-Hant": "繁體中文",
    "ja": "日本語",
    "ko": "한국어",
    "en": "English",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
    "pt": "Português",
    "ru": "Русский",
}

PROXY_MODE_OPTIONS: dict[str, str] = {
    PROXY_MODE_SYSTEM: "Use System Proxy",
    PROXY_MODE_CUSTOM: "Use Custom Proxy",
    PROXY_MODE_DISABLED: "No Proxy",
}

SUBTITLE_MODE_OPTIONS: dict[str, str] = {
    SUBTITLE_MODE_SOFT: "Soft Subtitle",
    SUBTITLE_MODE_HARD: "Hard Subtitle",
}


def _register_proxy_i18n_keys() -> None:
    QCoreApplication.translate("ProxyMode", "Use System Proxy")
    QCoreApplication.translate("ProxyMode", "Use Custom Proxy")
    QCoreApplication.translate("ProxyMode", "No Proxy")


def _register_subtitle_mode_i18n_keys() -> None:
    QCoreApplication.translate("SubtitleMode", "Soft Subtitle")
    QCoreApplication.translate("SubtitleMode", "Hard Subtitle")


def _register_language_i18n_keys() -> None:
    QCoreApplication.translate("LanguageOption", "System Language")


def format_proxy_mode_label(mode: str) -> str:
    label = PROXY_MODE_OPTIONS.get(mode, "Use System Proxy")
    return QCoreApplication.translate("ProxyMode", label)


def format_subtitle_mode_label(mode: str) -> str:
    label = SUBTITLE_MODE_OPTIONS.get(mode, "Soft Subtitle")
    return QCoreApplication.translate("SubtitleMode", label)


_register_proxy_i18n_keys()
_register_language_i18n_keys()
_register_subtitle_mode_i18n_keys()
