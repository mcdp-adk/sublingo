from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QWizard

from sublingo.gui.main_window import MainWindow
from sublingo.gui.pages.home import HomePage
from sublingo.gui.pages.settings import SettingsPage
from sublingo.gui.models.task import TaskType
from sublingo.gui.setup_wizard import SetupWizard

SETTINGS_SECTION_TITLES = {
    "GUI",
    "翻译",
    "Cookie",
    "输出路径",
    "AI",
    "代理",
    "维护",
}

WIZARD_TITLES = [
    "Language Settings",
    "AI Configuration",
    "Other Settings",
]


@pytest.fixture
def main_window(qtbot, gui_config_mgr, mock_core_modules) -> MainWindow:
    window = MainWindow(gui_config_mgr)
    qtbot.addWidget(window)
    window.show()
    return window


def test_main_window_launches_without_crash(main_window: MainWindow) -> None:
    assert main_window.isVisible() is True
    assert main_window.statusBar().currentMessage() == "Ready"
    assert main_window.page("home") is not None
    assert main_window.page("tasks") is not None
    assert main_window.page("settings") is not None


def test_main_window_navigation_reaches_all_pages(
    qtbot, main_window: MainWindow
) -> None:
    expected_pages = ((0, "home"), (1, "tasks"), (2, "settings"))

    for row, page_name in expected_pages:
        main_window._sidebar.setCurrentRow(row)
        qtbot.waitUntil(
            lambda name=page_name: (
                main_window._stack.currentWidget() is main_window.page(name)
            )
        )


def test_setup_wizard_pages_can_be_traversed(
    qtbot,
    gui_config_mgr,
    mock_core_modules,
) -> None:
    wizard = SetupWizard(gui_config_mgr)
    qtbot.addWidget(wizard)
    wizard.show()

    next_button = wizard.button(QWizard.WizardButton.NextButton)
    back_button = wizard.button(QWizard.WizardButton.BackButton)
    finish_button = wizard.button(QWizard.WizardButton.FinishButton)

    assert wizard.currentPage().title() == WIZARD_TITLES[0]
    assert back_button.isEnabled() is False

    qtbot.mouseClick(next_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: wizard.currentPage().title() == WIZARD_TITLES[1])

    qtbot.mouseClick(next_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: wizard.currentPage().title() == WIZARD_TITLES[2])
    assert finish_button.isEnabled() is True

    qtbot.mouseClick(back_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: wizard.currentPage().title() == WIZARD_TITLES[1])


def test_settings_page_loads_all_sections(
    qtbot,
    gui_config_mgr,
    mock_core_modules,
) -> None:
    page = SettingsPage(gui_config_mgr)
    qtbot.addWidget(page)
    page.show()

    group_titles = {group.title() for group in page.findChildren(QGroupBox)}
    assert SETTINGS_SECTION_TITLES.issubset(group_titles)


def test_home_page_task_type_selector_switches_forms(
    qtbot,
    gui_config_mgr,
    mock_core_modules,
) -> None:
    page = HomePage(gui_config_mgr)
    qtbot.addWidget(page)
    page.show()

    translate_index = page._task_type.findData(TaskType.TRANSLATE.value)
    download_index = page._task_type.findData(TaskType.DOWNLOAD.value)

    assert page._form_stack.currentWidget() is page._workflow_form
    assert page._preview_btn.isVisible() is True

    page._task_type.setCurrentIndex(translate_index)
    qtbot.waitUntil(lambda: page._form_stack.currentWidget() is page._translate_form)
    assert page._preview_btn.isVisible() is False

    page._task_type.setCurrentIndex(download_index)
    qtbot.waitUntil(lambda: page._form_stack.currentWidget() is page._download_form)
    assert page._preview_btn.isVisible() is True
