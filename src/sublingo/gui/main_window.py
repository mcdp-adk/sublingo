from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QWidget,
)

from sublingo import __version__
from sublingo.core.config import ConfigManager
from sublingo.gui.models.task import TaskManager
from sublingo.gui.pages.home import HomePage
from sublingo.gui.pages.settings import SettingsPage
from sublingo.gui.pages.tasks import TasksPage

_PAGE_INDEX_ROLE = Qt.ItemDataRole.UserRole + 1


class MainWindow(QMainWindow):
    """Application main window with sidebar navigation."""

    def __init__(
        self, config_mgr: ConfigManager, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._config_mgr = config_mgr
        self._task_mgr = TaskManager(config_mgr, self)

        self.setWindowTitle(f"Sublingo v{__version__}")
        self.setMinimumSize(900, 600)

        # -- Central widget & layout -----------------------------------------
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # -- Sidebar ----------------------------------------------------------
        self._sidebar = QListWidget()
        self._sidebar.setFixedWidth(200)
        self._sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._sidebar.setStyleSheet(
            """
            QListWidget {
                border: none;
                border-right: 1px solid palette(mid);
                background: palette(window);
                outline: none;
            }
            QListWidget::item {
                padding: 8px 16px;
            }
            QListWidget::item:selected {
                background: palette(highlight);
                color: palette(highlighted-text);
            }
            QListWidget::item:hover:!selected {
                background: palette(midlight);
            }
            """
        )
        root_layout.addWidget(self._sidebar)

        # -- Stacked content area ---------------------------------------------
        self._stack = QStackedWidget()
        root_layout.addWidget(self._stack, stretch=1)

        # -- Pages dict (name -> QWidget) for later replacement ---------------
        self._pages: dict[str, QWidget] = {}

        # -- Build sidebar items & placeholder pages --------------------------
        self._build_sidebar()

        # -- Replace placeholders with real pages -----------------------------
        home_page = HomePage(config_mgr, self._task_mgr)
        self.set_page("home", home_page)

        tasks_page = TasksPage(self._task_mgr)
        self.set_page("tasks", tasks_page)

        settings_page = SettingsPage(config_mgr)
        self.set_page("settings", settings_page)

        # -- Connect signals --------------------------------------------------
        settings_page.debug_mode_changed.connect(
            tasks_page.detail_widget.log_viewer.set_debug_mode
        )
        home_page.navigate_requested.connect(self._navigate_to_page)

        # -- Status bar -------------------------------------------------------
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage(self.tr("Ready"))

        # -- Connect sidebar selection to page switch -------------------------
        self._sidebar.currentItemChanged.connect(self._on_sidebar_item_changed)

        # -- Select the first selectable item (Home) --------------------------
        self._sidebar.setCurrentRow(0)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def page(self, name: str) -> QWidget | None:
        """Return the page widget registered under *name*, or ``None``."""
        return self._pages.get(name)

    def set_page(self, name: str, widget: QWidget) -> None:
        """Replace an existing placeholder page with a real widget."""
        old = self._pages.get(name)
        if old is None:
            return
        idx = self._stack.indexOf(old)
        if idx < 0:
            return
        self._stack.removeWidget(old)
        old.deleteLater()
        self._stack.insertWidget(idx, widget)
        self._pages[name] = widget

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_sidebar(self) -> None:
        """Populate the sidebar and create placeholder pages."""

        def _add_placeholder(name: str) -> int:
            widget = QWidget()
            idx = self._stack.addWidget(widget)
            self._pages[name] = widget
            return idx

        def _add_page_item(text: str, page_name: str) -> None:
            item = QListWidgetItem(text)
            item.setData(_PAGE_INDEX_ROLE, _add_placeholder(page_name))
            self._sidebar.addItem(item)

        _add_page_item(self.tr("Home"), "home")
        _add_page_item(self.tr("Tasks"), "tasks")
        _add_page_item(self.tr("Settings"), "settings")

    def _on_sidebar_item_changed(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        if current is None:
            return
        page_idx = current.data(_PAGE_INDEX_ROLE)
        if page_idx is None:
            return
        self._stack.setCurrentIndex(page_idx)

    def _navigate_to_page(self, page_name: str) -> None:
        """Navigate to the page associated with *page_name* by selecting the sidebar item."""
        target_widget = self._pages.get(page_name)
        if target_widget is None:
            return
        target_idx = self._stack.indexOf(target_widget)
        if target_idx < 0:
            return
        for row in range(self._sidebar.count()):
            item = self._sidebar.item(row)
            if item is not None and item.data(_PAGE_INDEX_ROLE) == target_idx:
                self._sidebar.setCurrentRow(row)
                return
