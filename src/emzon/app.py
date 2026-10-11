"""Entry point."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtGui import QSurfaceFormat
from PySide6.QtWidgets import QApplication

from emzon.media.tools import bundled_dir
from emzon.ui import strings, theme


def main() -> int:
    # libmpv is looked up on PATH when the player module is imported.
    os.environ["PATH"] = f"{bundled_dir()}{os.pathsep}{os.environ.get('PATH', '')}"

    if sys.platform == "darwin":
        surface = QSurfaceFormat()
        surface.setVersion(3, 2)
        surface.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        QSurfaceFormat.setDefaultFormat(surface)

    app = QApplication(sys.argv)
    app.setApplicationName(strings.APP_NAME)
    theme.load_fonts()
    app.setFont(theme.ui_font(13))
    app.setStyleSheet(theme.STYLESHEET)

    from emzon.window import MainWindow

    window = MainWindow()
    window.show()
    if len(sys.argv) > 1:
        window.open_path(Path(sys.argv[1]))
    return app.exec()
