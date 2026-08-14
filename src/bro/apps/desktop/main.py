from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from bro.apps.desktop.ui.main_window import MainWindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("bro")
    app.setOrganizationName("bro")
    window = MainWindow()
    window.show()
    return app.exec()


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
