"""Frames for the video lane, decoded in the background and kept in memory."""

from __future__ import annotations

import logging
import threading
from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

from emzon.media.tools import find_tool, run

log = logging.getLogger(__name__)

HEIGHT = 96
CACHE_SIZE = 600
WORKERS = 2
TIMEOUT = 20

Key = tuple[Path, float, bool]


def grab(path: Path, time: float, accurate: bool) -> QImage:
    args = [find_tool("ffmpeg"), "-v", "error", "-ss", f"{time:.3f}"]
    if not accurate:
        args.append("-noaccurate_seek")
    args += ["-i", path, "-frames:v", "1", "-vf", f"scale=-2:{HEIGHT}", "-f", "image2pipe", "-c:v", "mjpeg", "-q:v", "5", "-"]
    result = run(args, timeout=TIMEOUT)
    image = QImage.fromData(result.stdout, "JPG")
    if result.returncode != 0 or image.isNull():
        raise RuntimeError(result.stderr.decode(errors="replace").strip() or "no frame")
    return image


class Thumbnails(QObject):
    ready = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cache: OrderedDict[Key, QImage | None] = OrderedDict()
        self._wanted: list[Key] = []
        self._busy: set[Key] = set()
        self._lock = threading.Condition()
        self._closing = False
        for number in range(WORKERS):
            threading.Thread(target=self._work, name=f"thumbnails-{number}", daemon=True).start()

    def get(self, path: Path, time: float, accurate: bool) -> QImage | None:
        """The frame if it is ready; otherwise it is queued and None comes back."""
        key = (path, round(time, 2), accurate)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            if key not in self._busy and key not in self._wanted:
                self._wanted.append(key)
                self._lock.notify()
        return None

    def keep_only(self, path: Path, times: set[tuple[float, bool]]) -> None:
        """Forget queued requests the view no longer shows."""
        with self._lock:
            self._wanted = [k for k in self._wanted if k[0] == path and (k[1], k[2]) in times]

    def forget(self, path: Path) -> None:
        with self._lock:
            self._wanted = [k for k in self._wanted if k[0] != path]
            for key in [k for k in self._cache if k[0] == path]:
                del self._cache[key]

    def shutdown(self) -> None:
        with self._lock:
            self._closing = True
            self._wanted.clear()
            self._lock.notify_all()

    def _work(self) -> None:
        while True:
            with self._lock:
                while not self._wanted and not self._closing:
                    self._lock.wait()
                if self._closing:
                    return
                key = self._wanted.pop()
                self._busy.add(key)
            try:
                image = grab(*key)
            except Exception as error:  # noqa: BLE001  one missing frame must not stop the others
                log.warning("thumbnail at %.2f s of %s: %s", key[1], key[0].name, error)
                image = None
            with self._lock:
                self._busy.discard(key)
                self._cache[key] = image
                while len(self._cache) > CACHE_SIZE:
                    self._cache.popitem(last=False)
            self.ready.emit()
