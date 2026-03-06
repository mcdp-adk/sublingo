from __future__ import annotations

# pyright: reportMissingImports=false

import os
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from sublingo.core.config import AppConfig, ConfigManager


COOKIE_OK_MESSAGE = "Cookie OK"
PREVIEW_VIDEO = SimpleNamespace(
    title="Demo Video",
    duration=42,
    url="https://example.com/demo",
)


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Provide a shared QApplication for pytest-qt smoke tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return cast(QApplication, app)


@pytest.fixture
def gui_config_mgr(tmp_path: Path) -> ConfigManager:
    """Create an isolated config manager for GUI tests."""
    project_root = tmp_path / "project"
    fonts_dir = project_root / "fonts"
    fonts_dir.mkdir(parents=True)

    config_mgr = ConfigManager(project_root)
    config_mgr.save(
        AppConfig(
            project_dir="./projects",
            output_dir="./output",
            target_language="zh-Hans",
            font_file="TestFont.ttf",
        )
    )
    (fonts_dir / "TestFont.ttf").write_text("font", encoding="utf-8")
    return config_mgr


@pytest.fixture
def mock_core_modules(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    """Patch GUI-facing core hooks so smoke tests stay offline and local."""
    from sublingo.gui import setup_wizard
    from sublingo.gui.models import task as task_model
    from sublingo.gui.pages import home, settings
    from sublingo.gui.wizards import other_settings_page

    mocks = {
        "home_validate_cookie_file": MagicMock(return_value=(True, COOKIE_OK_MESSAGE)),
        "settings_validate_cookie_file": MagicMock(
            return_value=(True, COOKIE_OK_MESSAGE)
        ),
        "wizard_validate_cookie_file": MagicMock(
            return_value=(True, COOKIE_OK_MESSAGE)
        ),
        "extract_playlist_info": MagicMock(return_value=[PREVIEW_VIDEO]),
        "save_cookie_text": MagicMock(return_value=(True, "Cookie saved")),
        "download": MagicMock(
            return_value=SimpleNamespace(success=True, video_title="Demo Video")
        ),
        "run_workflow": MagicMock(
            return_value=SimpleNamespace(
                success=True,
                current_stage="complete",
                video_title="Demo Video",
            )
        ),
        "translate": MagicMock(return_value=SimpleNamespace(success=True)),
        "softsub": MagicMock(return_value=SimpleNamespace(success=True)),
        "hardsub": MagicMock(return_value=SimpleNamespace(success=True)),
        "generate_transcript": MagicMock(return_value=SimpleNamespace(success=True)),
        "subset_font": MagicMock(return_value=SimpleNamespace(success=True)),
        "load_translator": MagicMock(return_value=None),
    }

    monkeypatch.setattr(
        home, "validate_cookie_file", mocks["home_validate_cookie_file"]
    )
    monkeypatch.setattr(home, "extract_playlist_info", mocks["extract_playlist_info"])
    monkeypatch.setattr(
        settings, "validate_cookie_file", mocks["settings_validate_cookie_file"]
    )
    monkeypatch.setattr(settings, "save_cookie_text", mocks["save_cookie_text"])
    monkeypatch.setattr(
        other_settings_page,
        "validate_cookie_file",
        mocks["wizard_validate_cookie_file"],
    )
    monkeypatch.setattr(
        setup_wizard,
        "validate_cookie_file",
        mocks["wizard_validate_cookie_file"],
    )
    monkeypatch.setattr(setup_wizard, "load_translator", mocks["load_translator"])

    monkeypatch.setattr(task_model, "download", mocks["download"])
    monkeypatch.setattr(task_model, "run_workflow", mocks["run_workflow"])
    monkeypatch.setattr(task_model, "translate", mocks["translate"])
    monkeypatch.setattr(task_model, "softsub", mocks["softsub"])
    monkeypatch.setattr(task_model, "hardsub", mocks["hardsub"])
    monkeypatch.setattr(
        task_model,
        "generate_transcript",
        mocks["generate_transcript"],
    )
    monkeypatch.setattr(task_model, "subset_font", mocks["subset_font"])
    return mocks
