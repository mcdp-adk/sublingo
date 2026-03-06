from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QCoreApplication

from sublingo.core.config import AI_PROVIDER_PRESETS
from sublingo.core.config import PROXY_MODE_CUSTOM
from sublingo.core.config import PROXY_MODE_DISABLED
from sublingo.core.config import PROXY_MODE_SYSTEM


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
    if translator is not None and code == "auto":
        name = translator(name)
    if code == "auto":
        return name
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


def _register_proxy_i18n_keys() -> None:
    QCoreApplication.translate("ProxyMode", "Use System Proxy")
    QCoreApplication.translate("ProxyMode", "Use Custom Proxy")
    QCoreApplication.translate("ProxyMode", "No Proxy")


def format_proxy_mode_label(mode: str) -> str:
    label = PROXY_MODE_OPTIONS.get(mode, "Use System Proxy")
    return QCoreApplication.translate("ProxyMode", label)


_register_proxy_i18n_keys()
