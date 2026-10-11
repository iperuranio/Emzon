"""Exports run one at a time in the background while editing goes on."""

from __future__ import annotations

import itertools
import logging
import os
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from send2trash import send2trash

from emzon.export.jobs import Kind, Request, command, destination, parse_progress
from emzon.media.tools import NO_WINDOW, find_tool
from emzon.ui import strings

log = logging.getLogger(__name__)

ERROR_LINES = 3


class State(Enum):
    WAITING = "waiting"
    RUNNING = "running"
    FINISHING = "finishing"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def active(self) -> bool:
        return self in (State.WAITING, State.RUNNING, State.FINISHING)


@dataclass(eq=False)
class Job:
    id: int
    request: Request
    state: State = State.WAITING
    progress: float = 0.0
    software: bool = False
    error: str = ""
    kept_original: bool = False
    note: str = ""
    process: subprocess.Popen | None = field(default=None, repr=False)

    @property
    def output(self) -> Path:
        return self.request.destination


class ExportQueue(QObject):
    changed = Signal()
    replace_ready = Signal(object)

    def __init__(self, parent=None, ffmpeg: Callable[[], Path] = lambda: find_tool("ffmpeg")) -> None:
        super().__init__(parent)
        self.jobs: list[Job] = []
        self._ffmpeg = ffmpeg
        self._ids = itertools.count(1)
        self._wake = threading.Condition()
        self._closing = False
        self._worker = threading.Thread(target=self._run, name="export", daemon=True)
        self._worker.start()

    # Called from the UI thread

    def add(self, request: Request) -> Job:
        job = Job(next(self._ids), request)
        with self._wake:
            self.jobs.append(job)
            self._wake.notify()
        self.changed.emit()
        return job

    def reserved(self) -> set[Path]:
        return {job.output for job in self.jobs if job.state.active}

    def replacing(self, source: Path) -> bool:
        return any(j.state.active and j.request.replace_original and j.request.source == source for j in self.jobs)

    def cancel(self, job: Job) -> None:
        with self._wake:
            if not job.state.active or job.state is State.FINISHING:
                return
            job.state = State.CANCELLED
            if job.process is not None:
                job.process.kill()
        self.changed.emit()

    def clear_finished(self) -> None:
        with self._wake:
            self.jobs = [job for job in self.jobs if job.state.active]
        self.changed.emit()

    def finish_replace(self, job: Job) -> None:
        """Move the original to the Recycle Bin and put the export in its place.

        Runs on the UI thread once the window has let go of the original.
        If the original cannot be moved, the export is kept as a copy instead.
        """
        source = job.request.source
        try:
            if source.exists():
                send2trash(source)
            os.replace(job.request.partial, job.output)
        except OSError as error:
            log.warning("could not replace %s: %s", source, error)
            job.kept_original = True
            job.error = str(error)
            fallback = destination(source, Kind.VIDEO, job.request.audio_format, None, self.reserved())
            try:
                os.replace(job.request.partial, fallback)
                job.request = replace(job.request, destination=fallback, replace_original=False)
            except OSError as second:
                log.error("could not keep %s: %s", job.request.partial, second)
                job.state = State.FAILED
                job.error = str(second)
                self.changed.emit()
                return
        job.state = State.DONE
        job.progress = 1.0
        self.changed.emit()

    def shutdown(self) -> None:
        """Cancel everything still in the queue and wait briefly for the cleanup."""
        with self._wake:
            self._closing = True
            for job in self.jobs:
                if job.state in (State.WAITING, State.RUNNING):
                    job.state = State.CANCELLED
                    if job.process is not None:
                        job.process.kill()
                elif job.state is State.FINISHING:
                    _remove(job.request.partial)
            self._wake.notify()
        self._worker.join(timeout=5)

    @property
    def busy(self) -> bool:
        return any(job.state.active for job in self.jobs)

    # Worker thread

    def _next(self) -> Job | None:
        with self._wake:
            while not self._closing:
                job = next((j for j in self.jobs if j.state is State.WAITING), None)
                if job is not None:
                    job.state = State.RUNNING
                    return job
                self._wake.wait()
        return None

    def _run(self) -> None:
        while (job := self._next()) is not None:
            self.changed.emit()
            try:
                self._export(job)
            except Exception as error:  # noqa: BLE001  a job must never take the queue down
                log.exception("export %s failed", job.request.destination)
                job.state = State.FAILED
                job.error = str(error) or type(error).__name__
            if job.state is not State.FINISHING:
                _remove(job.request.partial)
            self.changed.emit()
            if job.state is State.FINISHING:
                self.replace_ready.emit(job)

    def _export(self, job: Job) -> None:
        request = job.request
        request.destination.parent.mkdir(parents=True, exist_ok=True)
        attempts = [True, False] if request.kind is Kind.VIDEO else [False]
        for hardware in attempts:
            job.software = not hardware and request.kind is Kind.VIDEO
            job.progress = 0.0
            succeeded, errors = self._encode(job, command(self._ffmpeg(), request, hardware))
            if job.state is State.CANCELLED:
                return
            if succeeded:
                break
            if hardware:
                log.info("hardware encoding failed, retrying in software: %s", errors[-ERROR_LINES:])
                continue
            job.state = State.FAILED
            job.error = "\n".join(errors[-ERROR_LINES:]) or strings.EXPORT_FAILED
            log.error("export %s failed: %s", request.destination, job.error)
            return

        if request.replace_original:
            job.state = State.FINISHING
        else:
            os.replace(request.partial, request.destination)
            job.state = State.DONE
            job.progress = 1.0

    def _encode(self, job: Job, args: list[str]) -> tuple[bool, list[str]]:
        with self._wake:
            if job.state is State.CANCELLED:
                return False, []
            job.process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=NO_WINDOW,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        errors: list[str] = []
        for line in job.process.stdout:
            fraction = parse_progress(line, job.request.duration)
            if fraction is not None:
                job.progress = fraction
                self.changed.emit()
            elif "=" not in line and line.strip():
                errors.append(line.strip())
        code = job.process.wait()
        job.process = None
        return code == 0, errors


def _remove(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError as error:
        log.warning("could not remove %s: %s", path, error)
