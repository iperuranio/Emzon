"""Locating and running the bundled FFmpeg tools."""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from pathlib import Path

# Background tools never show a console and yield to whatever else runs, games first.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)

_running: dict[subprocess.Popen, str] = {}
_lock = threading.Lock()


class ToolMissing(RuntimeError):
    pass


def bundled_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "vendor"
    return Path(__file__).resolve().parents[3] / "vendor"


def find_tool(name: str) -> Path:
    executable = f"{name}.exe" if sys.platform == "win32" else name
    bundled = bundled_dir() / executable
    if bundled.is_file():
        return bundled
    found = shutil.which(name)
    if found:
        return Path(found)
    raise ToolMissing(name)


def run(
    args: list[str | Path], *, timeout: float | None = None, group: str = ""
) -> subprocess.CompletedProcess[bytes]:
    """Run a tool to completion. Processes of a group can be stopped with `stop_group`."""
    process = subprocess.Popen(
        [str(a) for a in args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=NO_WINDOW,
    )
    with _lock:
        _running[process] = group
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
    finally:
        with _lock:
            _running.pop(process, None)
    return subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)


class Stream:
    """A running tool whose output is read as it comes; stoppable like `run`."""

    def __init__(self, args: list[str | Path], group: str = "") -> None:
        self.process = subprocess.Popen(
            [str(a) for a in args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=NO_WINDOW,
        )
        with _lock:
            _running[self.process] = group

    def __enter__(self) -> subprocess.Popen:
        return self.process

    def __exit__(self, *_) -> None:
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait()
        with _lock:
            _running.pop(self.process, None)


def stop_group(group: str) -> None:
    with _lock:
        processes = [p for p, g in _running.items() if g == group]
    for process in processes:
        process.kill()


def stop_all() -> None:
    with _lock:
        processes = list(_running)
    for process in processes:
        process.kill()
