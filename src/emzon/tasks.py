"""Running slow work off the UI thread and getting the result back on it."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal


class Tasks(QObject):
    """A few daemon workers, so pending work never keeps the app from quitting."""

    finished = Signal(object, object, object)

    def __init__(self, parent=None, workers: int = 2) -> None:
        super().__init__(parent)
        self._jobs: queue.Queue = queue.Queue()
        for number in range(workers):
            threading.Thread(target=self._work, name=f"tasks-{number}", daemon=True).start()

    def submit(self, key: object, function: Callable, *args) -> None:
        """Run function(*args); emit finished(key, result, error) when it is done."""
        self._jobs.put((key, function, args))

    def _work(self) -> None:
        while True:
            key, function, args = self._jobs.get()
            try:
                result, error = function(*args), None
            except Exception as failure:  # noqa: BLE001  reported to the UI thread
                result, error = None, failure
            try:
                self.finished.emit(key, result, error)
            except RuntimeError:
                return  # the window is gone

    def shutdown(self) -> None:
        """Drop work that has not started yet."""
        while True:
            try:
                self._jobs.get_nowait()
            except queue.Empty:
                return
