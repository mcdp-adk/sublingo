from __future__ import annotations

from collections.abc import Callable

from sublingo.core.config import AI_PROVIDER_PRESETS


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
