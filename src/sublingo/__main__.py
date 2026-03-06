from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from sublingo.core.config import ConfigManager
from sublingo.gui.main_window import MainWindow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="sublingo",
        description="Cross-platform desktop GUI app for video subtitle translation",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with verbose logging",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = QApplication(sys.argv)
    project_root = Path(__file__).resolve().parent.parent.parent
    config_mgr = ConfigManager(project_root)

    # Load project font to fix missing glyphs in WSL/Linux
    font_path = project_root / "fonts" / "LXGWWenKai-Regular.ttf"
    if font_path.exists():
        QFontDatabase.addApplicationFont(str(font_path))
        app.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))

    if config_mgr.is_first_run:
        # TODO: Show Setup Wizard
        pass

    window = MainWindow(config_mgr)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
