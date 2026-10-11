"""Talking to the copy of Emzon that is already open.

The open copy listens on a local channel (a named pipe on Windows). Started
with `--quit`, Emzon asks that copy to close and exits without opening a
window; the open copy closes cleanly unless an export is running.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

log = logging.getLogger(__name__)

QUIT = "quit"
CLOSING = "closing"
BUSY = "busy"
TIMEOUT_MS = 3000


def server_name() -> str:
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
    return "dev.metessi.emzon-" + re.sub(r"[^A-Za-z0-9_.-]", "_", user)


def request_quit(timeout_ms: int = TIMEOUT_MS) -> str | None:
    """Ask the open copy to close. Its answer, or None when no copy is open."""
    socket = QLocalSocket()
    socket.connectToServer(server_name())
    if not socket.waitForConnected(timeout_ms):
        return None
    socket.write(f"{QUIT}\n".encode())
    socket.flush()
    socket.waitForBytesWritten(timeout_ms)
    answer = ""
    while socket.waitForReadyRead(timeout_ms):
        answer += bytes(socket.readAll()).decode(errors="replace")
        if answer.endswith("\n"):
            break
    socket.disconnectFromServer()
    return answer.strip()


class InstanceServer(QObject):
    """Answers requests from later copies. `can_quit` decides, and does the closing when it can."""

    quit_accepted = Signal()

    def __init__(self, can_quit: Callable[[], bool], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._can_quit = can_quit
        self._server = QLocalServer(self)
        self._server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self._server.newConnection.connect(self._accept)

    def listen(self) -> bool:
        name = server_name()
        if not self._server.listen(name):
            # A copy that crashed may have left its socket behind (not on Windows, where pipes vanish).
            QLocalServer.removeServer(name)
            if not self._server.listen(name):
                log.warning("cannot listen on %s: %s", name, self._server.errorString())
                return False
        return True

    def close(self) -> None:
        self._server.close()

    def _accept(self) -> None:
        while (socket := self._server.nextPendingConnection()) is not None:
            socket.readyRead.connect(lambda s=socket: self._read(s))
            socket.disconnected.connect(socket.deleteLater)

    def _read(self, socket: QLocalSocket) -> None:
        while socket.canReadLine():
            line = bytes(socket.readLine()).decode(errors="replace").strip()
            if line != QUIT:
                continue
            closing = self._can_quit()
            log.info("asked to quit: %s", CLOSING if closing else BUSY)
            socket.write(f"{CLOSING if closing else BUSY}\n".encode())
            socket.flush()
            if closing:
                self.quit_accepted.emit()
