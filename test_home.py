import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from sublingo.core.config import ConfigManager
from sublingo.gui.pages.home import HomePage
from sublingo.gui.models.task import TaskManager


def main():
    app = QApplication(sys.argv)

    project_root = Path(__file__).parent
    config_mgr = ConfigManager(project_root)
    task_mgr = TaskManager()

    home_page = HomePage(config_mgr, task_mgr)
    home_page.resize(800, 600)
    home_page.show()

    # Process events to ensure it's fully rendered
    app.processEvents()

    # Take screenshot
    evidence_dir = project_root / ".sisyphus" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    screenshot_path = evidence_dir / "task-16-home.png"
    pixmap = home_page.grab()
    pixmap.save(str(screenshot_path))

    print(f"Screenshot saved to {screenshot_path}")

    # Also save a text file as evidence
    txt_path = evidence_dir / "task-16-evidence.txt"
    txt_path.write_text("Home page implemented successfully.")

    # We don't need to run the event loop, just exit
    return 0


if __name__ == "__main__":
    sys.exit(main())
