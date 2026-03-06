"""Configuration management for Sublingo."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from sublingo.core.constants import (
    AI_DEFAULT_MODEL,
    AI_MAX_RETRIES,
    AI_TRANSLATION_BATCH_SIZE,
    CONFIG_DEFAULT_API_BASE_GEMINI,
    CONFIG_DEFAULT_FONT,
)


@dataclass
class AppConfig:
    """Application configuration with sensible defaults."""

    # Output paths
    project_dir: str = "./output"
    output_dir: str = "./output"

    # Translation
    target_language: str = "zh-Hans"
    generate_transcript: bool = False

    # Font
    font_file: str = CONFIG_DEFAULT_FONT

    # AI settings
    ai_provider: str = "gemini"
    ai_base_url: str = CONFIG_DEFAULT_API_BASE_GEMINI
    ai_model: str = AI_DEFAULT_MODEL
    ai_api_key: str = ""
    ai_translate_batch_size: int = 20
    ai_proofread_batch_size: int = AI_TRANSLATION_BATCH_SIZE
    ai_segment_batch_size: int = AI_TRANSLATION_BATCH_SIZE
    ai_max_retries: int = AI_MAX_RETRIES

    # Network
    proxy: str = ""  # Empty string means no proxy
    batch_delay_seconds: int = 0

    # GUI
    language: str = "auto"
    debug_mode: bool = False


# Backward compatibility mapping for old language codes
_LANGUAGE_COMPAT_MAP: dict[str, str] = {
    "zh-CN": "zh-Hans",
    "zh-TW": "zh-Hant",
}


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
        raw = self.config.project_dir
        p = Path(raw)
        if p.is_absolute():
            return p.resolve()
        return (self._project_root / raw).resolve()

    def resolve_output_dir(self) -> Path:
        """Resolve output_dir relative to project_root."""
        raw = self.config.output_dir
        p = Path(raw)
        if p.is_absolute():
            return p.resolve()
        return (self._project_root / raw).resolve()
