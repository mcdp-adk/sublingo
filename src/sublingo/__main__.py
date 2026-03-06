from __future__ import annotations

import sys
from importlib import import_module


def main() -> int:
    qt_widgets = import_module("PySide6.QtWidgets")
    QApplication = qt_widgets.QApplication
    QWidget = qt_widgets.QWidget
    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle("Sublingo")
    window.resize(960, 640)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
