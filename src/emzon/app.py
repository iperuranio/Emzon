"""Entry point."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtGui import QIcon, QSurfaceFormat
from PySide6.QtWidgets import QApplication

from emzon import __version__, logs
from emzon.media.tools import bundled_dir
from emzon.start_menu import keep_start_menu_shortcut
from emzon.ui import strings, theme

APP_USER_MODEL_ID = "dev.metessi.emzon"
ICON = Path(__file__).with_name("ui") / "icon.png"


QUIT_FLAG = "--quit"


def main() -> int:
    if QUIT_FLAG in sys.argv:
        # Ask the open copy to close and leave; no window, no log, no shortcut.
        from emzon.single import request_quit

        QCoreApplication(sys.argv[:1])
        request_quit()
        return 0

    # libmpv is looked up on PATH when the player module is imported.
    os.environ["PATH"] = f"{bundled_dir()}{os.pathsep}{os.environ.get('PATH', '')}"

    if "--self-test" in sys.argv:
        from emzon.selftest import run_checks

        position = sys.argv.index("--self-test")
        report = sys.argv[position + 1] if len(sys.argv) > position + 1 else "self-test.json"
        return run_checks(Path(report))

    if sys.platform == "darwin":
        surface = QSurfaceFormat()
        surface.setVersion(3, 2)
        surface.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        QSurfaceFormat.setDefaultFormat(surface)

    app = QApplication(sys.argv)
    app.setApplicationName(strings.APP_NAME)
    app.setOrganizationName("Metessi")
    app.setApplicationVersion(__version__)
    log_file = logs.setup()
    logging.getLogger(__name__).info("Emzon %s starting, log at %s", __version__, log_file)
    keep_start_menu_shortcut(strings.APP_NAME, APP_USER_MODEL_ID)

    app.setStyle("Fusion")
    app.setPalette(theme.palette())
    theme.load_fonts()
    app.setFont(theme.ui_font(13))
    app.setStyleSheet(theme.STYLESHEET)
    if ICON.is_file():
        app.setWindowIcon(QIcon(str(ICON)))

    from emzon.window import MainWindow

    from emzon.single import InstanceServer

    window = MainWindow()
    server = InstanceServer(window.can_quit, app)
    server.quit_accepted.connect(lambda: QTimer.singleShot(0, window.quit_cleanly))
    server.listen()
    window.show()
    arguments = [a for a in sys.argv[1:] if not a.startswith("-")]
    if arguments:
        window.open_path(Path(arguments[0]))
    return app.exec()
