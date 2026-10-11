"""Running slow work off the UI thread and getting the result back on it."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor

from PySide6.QtCore import QObject, Signal


class Tasks(QObject):
    finished = Signal(object, object, object)

    def __init__(self, parent=None, workers: int = 2) -> None:
        super().__init__(parent)
        self._pool = ThreadPoolExecutor(max_workers=workers)

    def submit(self, key: object, function: Callable, *args) -> None:
        """Run function(*args); emit finished(key, result, error) when it is done."""
        future = self._pool.submit(function, *args)
        future.add_done_callback(lambda done: self._report(key, done))

    def _report(self, key: object, future: Future) -> None:
        error = future.exception()
        self.finished.emit(key, None if error else future.result(), error)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
