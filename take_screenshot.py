import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from sublingo.core.config import ConfigManager
from sublingo.gui.pages.settings import SettingsPage


def main():
    app = QApplication(sys.argv)

    project_root = Path(__file__).parent.resolve()
    config_mgr = ConfigManager(project_root)

    page = SettingsPage(config_mgr)
    page.resize(800, 600)
    page.show()

    # Process events to ensure it's fully rendered
    app.processEvents()

    # Create evidence directory
    evidence_dir = project_root / ".sisyphus" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # Grab screenshot
    pixmap = page.grab()
    pixmap.save(str(evidence_dir / "task-15-settings.png"))

    # Also save a text evidence file
    (evidence_dir / "task-15-settings.txt").write_text(
        "Settings page implemented and screenshot taken."
    )

    print("Screenshot saved.")


if __name__ == "__main__":
    main()
