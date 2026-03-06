"""Tests for configuration management."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from sublingo.core.config import (
    AppConfig,
    ConfigManager,
    DEFAULT_AI_BASE_URL,
    DEFAULT_AI_MODEL,
    DEFAULT_AI_PROVIDER,
    DEFAULT_FONT_FILE,
    DEFAULT_PROXY_MODE,
    DEFAULT_SUBTITLE_MODE,
    PROXY_MODE_CUSTOM,
    PROXY_MODE_DISABLED,
    PROXY_MODE_SYSTEM,
    SUBTITLE_MODE_HARD,
)
from sublingo.core.constants import (
    AI_MAX_RETRIES,
    AI_PROOFREADING_BATCH_SIZE,
    AI_TRANSLATION_BATCH_SIZE,
)
from sublingo.core.network_policy import resolve_download_proxy
from sublingo.core.network_policy import resolve_http_proxy_from_values
from sublingo.core.network_policy import resolve_http_proxy_policy


class TestAppConfig:
    """Tests for AppConfig dataclass."""

    def test_default_values(self) -> None:
        """Test that AppConfig has correct default values."""
        config = AppConfig()

        # Paths
        assert config.project_dir == "./output"
        assert config.output_dir == "./output"

        # Translation
        assert config.target_language == "auto"
        assert config.generate_transcript is False
        assert config.subtitle_mode == DEFAULT_SUBTITLE_MODE

        # Font
        assert config.font_file == DEFAULT_FONT_FILE
        assert config.font_file == "LXGWWenKai-Medium.ttf"

        # AI settings
        assert config.ai_provider == DEFAULT_AI_PROVIDER
        assert config.ai_base_url == DEFAULT_AI_BASE_URL
        assert config.ai_model == DEFAULT_AI_MODEL
        assert config.ai_model == "gpt-5-mini"
        assert config.ai_api_key == ""
        assert config.ai_translate_batch_size == AI_TRANSLATION_BATCH_SIZE
        assert config.ai_proofread_batch_size == AI_PROOFREADING_BATCH_SIZE
        assert config.ai_segment_batch_size == AI_TRANSLATION_BATCH_SIZE
        assert config.ai_max_retries == AI_MAX_RETRIES

        # Network
        assert config.proxy_mode == DEFAULT_PROXY_MODE
        assert config.proxy == ""
        assert config.batch_delay_seconds == 0

        # GUI
        assert config.language == "auto"
        assert config.debug_mode is False

    def test_field_order(self) -> None:
        """Test that fields are in expected order."""
        from dataclasses import fields

        field_names = [f.name for f in fields(AppConfig)]
        expected_order = [
            "project_dir",
            "output_dir",
            "target_language",
            "generate_transcript",
            "subtitle_mode",
            "font_file",
            "ai_provider",
            "ai_base_url",
            "ai_model",
            "ai_api_key",
            "ai_translate_batch_size",
            "ai_proofread_batch_size",
            "ai_segment_batch_size",
            "ai_max_retries",
            "proxy_mode",
            "proxy",
            "batch_delay_seconds",
            "language",
            "debug_mode",
        ]
        assert field_names == expected_order

    def test_custom_values(self) -> None:
        """Test that custom values can be set."""
        config = AppConfig(
            project_dir="./custom_project",
            output_dir="./custom_output",
            target_language="en",
            generate_transcript=True,
            subtitle_mode=SUBTITLE_MODE_HARD,
            ai_provider="openai",
            ai_model="gpt-4",
            proxy_mode=PROXY_MODE_CUSTOM,
            proxy="http://proxy.example.com:8080",
            debug_mode=True,
        )

        assert config.project_dir == "./custom_project"
        assert config.output_dir == "./custom_output"
        assert config.target_language == "en"
        assert config.generate_transcript is True
        assert config.subtitle_mode == SUBTITLE_MODE_HARD
        assert config.ai_provider == "openai"
        assert config.ai_model == "gpt-4"
        assert config.proxy_mode == PROXY_MODE_CUSTOM
        assert config.proxy == "http://proxy.example.com:8080"
        assert config.debug_mode is True


class TestConfigManager:
    """Tests for ConfigManager class."""

    @pytest.fixture
    def temp_dir(self) -> Iterator[Path]:
        """Provide a temporary directory."""
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    @pytest.fixture
    def manager(self, temp_dir: Path) -> ConfigManager:
        """Provide a ConfigManager instance with temp directory."""
        return ConfigManager(temp_dir)

    def test_init(self, manager: ConfigManager, temp_dir: Path) -> None:
        """Test ConfigManager initialization."""
        assert manager.project_root == temp_dir
        assert manager.config_file == temp_dir / "config.json"
        assert manager.cookie_file == temp_dir / "cookies.txt"

    def test_is_first_run_true(self, manager: ConfigManager) -> None:
        """Test is_first_run returns True when config doesn't exist."""
        assert manager.is_first_run is True

    def test_is_first_run_false(self, manager: ConfigManager) -> None:
        """Test is_first_run returns False when config exists."""
        # Create config file
        manager.config_file.write_text("{}")
        assert manager.is_first_run is False

    def test_load_default_config(self, manager: ConfigManager) -> None:
        """Test loading when config file doesn't exist returns defaults."""
        config = manager.load()
        assert isinstance(config, AppConfig)
        assert config.ai_provider == "openai"
        assert config.target_language == "auto"

    def test_load_existing_config(self, manager: ConfigManager) -> None:
        """Test loading existing config file."""
        data = {
            "ai_provider": "openai",
            "target_language": "en",
            "generate_transcript": True,
        }
        manager.config_file.write_text(json.dumps(data))

        config = manager.load()
        assert config.ai_provider == "openai"
        assert config.target_language == "en"
        assert config.generate_transcript is True
        # Other fields should be defaults
        assert config.ai_model == DEFAULT_AI_MODEL

    def test_load_infers_custom_proxy_mode_for_legacy_proxy(
        self, manager: ConfigManager
    ) -> None:
        data = {"proxy": "http://127.0.0.1:7890"}
        manager.config_file.write_text(json.dumps(data))

        config = manager.load()

        assert config.proxy_mode == PROXY_MODE_CUSTOM
        assert config.proxy == "http://127.0.0.1:7890"

    def test_load_normalizes_invalid_proxy_mode(self, manager: ConfigManager) -> None:
        data = {"proxy_mode": "invalid"}
        manager.config_file.write_text(json.dumps(data))

        config = manager.load()

        assert config.proxy_mode == PROXY_MODE_SYSTEM

    def test_load_normalizes_invalid_subtitle_mode(
        self, manager: ConfigManager
    ) -> None:
        data = {"subtitle_mode": "invalid"}
        manager.config_file.write_text(json.dumps(data))

        config = manager.load()

        assert config.subtitle_mode == DEFAULT_SUBTITLE_MODE

    def test_load_filters_unknown_fields(self, manager: ConfigManager) -> None:
        """Test that unknown fields are filtered out."""
        data = {
            "ai_provider": "openai",
            "unknown_field": "should_be_filtered",
            "another_unknown": 123,
        }
        manager.config_file.write_text(json.dumps(data))

        config = manager.load()
        assert config.ai_provider == "openai"
        # Should not raise error for unknown fields
        assert not hasattr(config, "unknown_field")

    def test_load_backward_compat_language(self, manager: ConfigManager) -> None:
        """Test backward compatibility for old language codes."""
        data = {"target_language": "zh-CN"}
        manager.config_file.write_text(json.dumps(data))

        config = manager.load()
        assert config.target_language == "zh-Hans"

        # Test zh-TW mapping
        data = {"target_language": "zh-TW"}
        manager.config_file.write_text(json.dumps(data))
        config = manager.load()
        assert config.target_language == "zh-Hant"

    def test_save_config(self, manager: ConfigManager) -> None:
        """Test saving configuration."""
        config = AppConfig(ai_provider="anthropic", target_language="ja")
        manager.save(config)

        # Verify file exists and contains correct data
        assert manager.config_file.exists()
        data = json.loads(manager.config_file.read_text())
        assert data["ai_provider"] == "anthropic"
        assert data["target_language"] == "ja"

    def test_save_creates_parent_dirs(self, temp_dir: Path) -> None:
        """Test that save creates parent directories."""
        nested_dir = temp_dir / "nested" / "deep"
        manager = ConfigManager(nested_dir)
        config = AppConfig()

        manager.save(config)
        assert manager.config_file.exists()

    def test_save_pretty_format(self, manager: ConfigManager) -> None:
        """Test that saved config is pretty-formatted with indentation."""
        config = AppConfig()
        manager.save(config)

        content = manager.config_file.read_text()
        # Should have indentation
        assert '  "' in content or '\n  "' in content
        # Should not be single line
        assert content.count("\n") > 1

    def test_save_caches_config(self, manager: ConfigManager) -> None:
        """Test that save updates the cached config."""
        config1 = AppConfig(ai_provider="openai")
        manager.save(config1)

        # Access config property should return cached version
        cached = manager.config
        assert cached.ai_provider == "openai"

    def test_reset_deletes_config(self, manager: ConfigManager) -> None:
        """Test reset deletes config file and clears cache."""
        # Create config
        manager.config_file.write_text("{}")
        manager._cached_config = AppConfig()

        manager.reset()

        assert not manager.config_file.exists()
        assert manager._cached_config is None

    def test_reset_no_error_if_no_file(self, manager: ConfigManager) -> None:
        """Test reset doesn't error if config file doesn't exist."""
        manager.reset()  # Should not raise
        assert not manager.config_file.exists()

    def test_get_default(self, manager: ConfigManager) -> None:
        """Test getting default values."""
        assert manager.get_default("ai_provider") == DEFAULT_AI_PROVIDER
        assert manager.get_default("target_language") == "auto"
        assert manager.get_default("ai_max_retries") == AI_MAX_RETRIES

    def test_get_default_unknown_field(self, manager: ConfigManager) -> None:
        """Test get_default returns None for unknown fields."""
        assert manager.get_default("unknown_field") is None

    def test_resolve_project_dir_relative(self, manager: ConfigManager) -> None:
        """Test resolving relative project_dir."""
        config = AppConfig(project_dir="./videos")
        manager.save(config)

        resolved = manager.resolve_project_dir()
        assert resolved == (manager.project_root / "videos").resolve()

    def test_resolve_project_dir_absolute(self, manager: ConfigManager) -> None:
        """Test resolving absolute project_dir."""
        absolute_path = "/tmp/absolute_project"
        config = AppConfig(project_dir=absolute_path)
        manager.save(config)

        resolved = manager.resolve_project_dir()
        assert resolved == Path(absolute_path).resolve()

    def test_resolve_output_dir_relative(self, manager: ConfigManager) -> None:
        """Test resolving relative output_dir."""
        config = AppConfig(output_dir="./output_videos")
        manager.save(config)

        resolved = manager.resolve_output_dir()
        assert resolved == (manager.project_root / "output_videos").resolve()

    def test_resolve_output_dir_absolute(self, manager: ConfigManager) -> None:
        """Test resolving absolute output_dir."""
        absolute_path = "/tmp/absolute_output"
        config = AppConfig(output_dir=absolute_path)
        manager.save(config)

        resolved = manager.resolve_output_dir()
        assert resolved == Path(absolute_path).resolve()

    def test_resolve_project_dir_windows_absolute_kept_as_absolute_text(
        self, manager: ConfigManager
    ) -> None:
        config = AppConfig(project_dir=r"C:\Users\joe\Videos")
        manager.save(config)

        resolved = manager.resolve_project_dir()
        assert str(resolved) == r"C:\Users\joe\Videos"

    def test_resolve_output_dir_windows_absolute_kept_as_absolute_text(
        self, manager: ConfigManager
    ) -> None:
        config = AppConfig(output_dir=r"D:\Sublingo\Output")
        manager.save(config)

        resolved = manager.resolve_output_dir()
        assert str(resolved) == r"D:\Sublingo\Output"

    def test_resolve_http_proxy_modes(self) -> None:
        system_policy = resolve_http_proxy_policy(
            AppConfig(proxy_mode=PROXY_MODE_SYSTEM, proxy="http://127.0.0.1:7890")
        )
        assert system_policy.proxy is None
        assert system_policy.trust_env is True

        custom_policy = resolve_http_proxy_policy(
            AppConfig(proxy_mode=PROXY_MODE_CUSTOM, proxy="http://127.0.0.1:7890")
        )
        assert custom_policy.proxy == "http://127.0.0.1:7890"
        assert custom_policy.trust_env is False

        disabled_policy = resolve_http_proxy_policy(
            AppConfig(proxy_mode=PROXY_MODE_DISABLED, proxy="http://127.0.0.1:7890")
        )
        assert disabled_policy.proxy is None
        assert disabled_policy.trust_env is False

    def test_resolve_http_proxy_from_values(self) -> None:
        policy = resolve_http_proxy_from_values("custom", "http://127.0.0.1:7890")
        assert policy.proxy == "http://127.0.0.1:7890"
        assert policy.trust_env is False

    def test_resolve_download_proxy_modes(self) -> None:
        assert (
            resolve_download_proxy(
                AppConfig(proxy_mode=PROXY_MODE_SYSTEM, proxy="http://127.0.0.1:7890")
            )
            is None
        )
        assert (
            resolve_download_proxy(
                AppConfig(proxy_mode=PROXY_MODE_CUSTOM, proxy="http://127.0.0.1:7890")
            )
            == "http://127.0.0.1:7890"
        )
        assert (
            resolve_download_proxy(
                AppConfig(proxy_mode=PROXY_MODE_DISABLED, proxy="http://127.0.0.1:7890")
            )
            == ""
        )

    def test_config_property_lazy_loads(self, manager: ConfigManager) -> None:
        """Test config property lazy loads on first access."""
        # No cached config initially
        assert manager._cached_config is None

        # First access should load
        config = manager.config
        assert isinstance(config, AppConfig)
        assert manager._cached_config is config

        # Second access should return cached
        config2 = manager.config
        assert config2 is config

    def test_load_updates_cache(self, manager: ConfigManager) -> None:
        """Test that load updates the cached config."""
        # Create a config file first
        config = AppConfig(ai_provider="openai")
        manager.save(config)

        # Reset cache
        manager._cached_config = None
        assert manager._cached_config is None

        # Load should update cache
        loaded = manager.load()
        assert manager._cached_config is loaded

    def test_load_returns_fresh_when_no_file(self, manager: ConfigManager) -> None:
        """Test that load returns fresh instance when no config file exists."""
        config1 = manager.load()
        config2 = manager.load()
        # When no file exists, load() returns new AppConfig() each time
        assert config1 is not config2
        # But they should be equal in value
        assert config1 == config2
