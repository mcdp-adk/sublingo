"""Configuration management for Sublingo."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from sublingo.core.constants import (
    AI_MAX_RETRIES,
    AI_PROOFREADING_BATCH_SIZE,
    AI_TRANSLATION_BATCH_SIZE,
)
from sublingo.core.path_policy import resolve_user_path

DEFAULT_PROJECT_DIR: str = "./output"
DEFAULT_OUTPUT_DIR: str = "./output"
DEFAULT_TARGET_LANGUAGE: str = "auto"
DEFAULT_GENERATE_TRANSCRIPT: bool = False
SUBTITLE_MODE_SOFT: str = "softsub"
SUBTITLE_MODE_HARD: str = "hardsub"
DEFAULT_SUBTITLE_MODE: str = SUBTITLE_MODE_SOFT
DEFAULT_FONT_FILE: str = "LXGWWenKai-Medium.ttf"
DEFAULT_AI_PROVIDER: str = "openai"
DEFAULT_AI_BASE_URL: str = "https://api.openai.com/v1"
DEFAULT_AI_MODEL: str = "gpt-5-mini"
DEFAULT_AI_API_KEY: str = ""
DEFAULT_AI_TRANSLATE_BATCH_SIZE: int = AI_TRANSLATION_BATCH_SIZE
DEFAULT_AI_PROOFREAD_BATCH_SIZE: int = AI_PROOFREADING_BATCH_SIZE
DEFAULT_AI_SEGMENT_BATCH_SIZE: int = AI_TRANSLATION_BATCH_SIZE
DEFAULT_AI_MAX_RETRIES: int = AI_MAX_RETRIES
PROXY_MODE_SYSTEM: str = "system"
PROXY_MODE_CUSTOM: str = "custom"
PROXY_MODE_DISABLED: str = "disabled"
DEFAULT_PROXY_MODE: str = PROXY_MODE_SYSTEM
DEFAULT_PROXY: str = ""
DEFAULT_BATCH_DELAY_SECONDS: int = 0
DEFAULT_GUI_LANGUAGE: str = "auto"
DEFAULT_DEBUG_MODE: bool = False

AI_PROVIDER_PRESETS: dict[str, tuple[str, str]] = {
    "openai": ("https://api.openai.com/v1", "gpt-5-mini"),
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "gemini-flash-latest",
    ),
    "deepseek": ("https://api.deepseek.com/v1", "deepseek-chat"),
    "openrouter": ("https://openrouter.ai/api/v1", "openrouter/auto"),
    "custom": ("", ""),
}


@dataclass
class AppConfig:
    """Application configuration with sensible defaults."""

    # Output paths
    project_dir: str = DEFAULT_PROJECT_DIR
    output_dir: str = DEFAULT_OUTPUT_DIR

    # Translation
    target_language: str = DEFAULT_TARGET_LANGUAGE
    generate_transcript: bool = DEFAULT_GENERATE_TRANSCRIPT
    subtitle_mode: str = DEFAULT_SUBTITLE_MODE

    # Font
    font_file: str = DEFAULT_FONT_FILE

    # AI settings
    ai_provider: str = DEFAULT_AI_PROVIDER
    ai_base_url: str = DEFAULT_AI_BASE_URL
    ai_model: str = DEFAULT_AI_MODEL
    ai_api_key: str = DEFAULT_AI_API_KEY
    ai_translate_batch_size: int = DEFAULT_AI_TRANSLATE_BATCH_SIZE
    ai_proofread_batch_size: int = DEFAULT_AI_PROOFREAD_BATCH_SIZE
    ai_segment_batch_size: int = DEFAULT_AI_SEGMENT_BATCH_SIZE
    ai_max_retries: int = DEFAULT_AI_MAX_RETRIES

    # Network
    proxy_mode: str = DEFAULT_PROXY_MODE
    proxy: str = DEFAULT_PROXY  # Empty string means no proxy
    batch_delay_seconds: int = DEFAULT_BATCH_DELAY_SECONDS

    # GUI
    language: str = DEFAULT_GUI_LANGUAGE
    debug_mode: bool = DEFAULT_DEBUG_MODE


# Backward compatibility mapping for old language codes
_LANGUAGE_COMPAT_MAP: dict[str, str] = {
    "zh-CN": "zh-Hans",
    "zh-TW": "zh-Hant",
}


def normalize_proxy_mode(value: str | None) -> str:
    mode = (value or "").strip().lower()
    if mode in {PROXY_MODE_SYSTEM, PROXY_MODE_CUSTOM, PROXY_MODE_DISABLED}:
        return mode
    return DEFAULT_PROXY_MODE


def normalize_subtitle_mode(value: str | None) -> str:
    mode = (value or "").strip().lower()
    if mode in {SUBTITLE_MODE_SOFT, SUBTITLE_MODE_HARD}:
        return mode
    return DEFAULT_SUBTITLE_MODE


class ConfigManager:
    """Manages loading, saving, and resolving application configuration."""

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root
        self._config_file = project_root / "config.json"
        self._cached_config: AppConfig | None = None

    @property
    def config_file(self) -> Path:
        """Path to the config.json file."""
        return self._config_file

    @property
    def project_root(self) -> Path:
        """Root directory of the project."""
        return self._project_root

    @property
    def cookie_file(self) -> Path:
        """Path to the cookies.txt file."""
        return self._project_root / "cookies.txt"

    @property
    def config(self) -> AppConfig:
        """Lazy-loaded configuration. Loads from file on first access."""
        if self._cached_config is None:
            self._cached_config = self.load()
        return self._cached_config

    @property
    def is_first_run(self) -> bool:
        """True if config.json does not exist yet."""
        return not self._config_file.exists()

    def load(self) -> AppConfig:
        """Load configuration from JSON file.

        Handles backward compatibility for old language codes and
        filters out unknown fields that are not part of AppConfig.
        Returns default AppConfig if file does not exist.
        """
        if not self._config_file.exists():
            return AppConfig()

        raw_text = self._config_file.read_text(encoding="utf-8")
        data: dict[str, Any] = json.loads(raw_text)

        # Backward compatibility: map old language codes
        if "target_language" in data:
            data["target_language"] = _LANGUAGE_COMPAT_MAP.get(
                data["target_language"], data["target_language"]
            )

        if "proxy_mode" in data:
            data["proxy_mode"] = normalize_proxy_mode(str(data["proxy_mode"]))
        elif str(data.get("proxy") or "").strip():
            data["proxy_mode"] = PROXY_MODE_CUSTOM

        if "subtitle_mode" in data:
            data["subtitle_mode"] = normalize_subtitle_mode(str(data["subtitle_mode"]))

        # Filter out unknown fields
        known_fields = {f.name for f in fields(AppConfig)}
        filtered = {k: v for k, v in data.items() if k in known_fields}

        self._cached_config = AppConfig(**filtered)
        return self._cached_config

    def save(self, config: AppConfig) -> None:
        """Save configuration to JSON file with pretty formatting."""
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(config)
        raw_text = json.dumps(data, indent=2, ensure_ascii=False)
        self._config_file.write_text(raw_text, encoding="utf-8")
        self._cached_config = config

    def reset(self) -> None:
        """Delete config.json and clear cached config."""
        if self._config_file.exists():
            self._config_file.unlink()
        self._cached_config = None

    def get_default(self, key: str) -> Any:
        """Get the default value for a config field. Returns None if unknown."""
        defaults = AppConfig()
        if hasattr(defaults, key):
            return getattr(defaults, key)
        return None

    def resolve_project_dir(self) -> Path:
        """Resolve project_dir relative to project_root."""
        return resolve_user_path(self.config.project_dir, self._project_root)

    def resolve_output_dir(self) -> Path:
        """Resolve output_dir relative to project_root."""
        return resolve_user_path(self.config.output_dir, self._project_root)
