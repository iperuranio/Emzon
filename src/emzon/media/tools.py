"""Locating and running the bundled FFmpeg tools."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class ToolMissing(RuntimeError):
    pass


def bundled_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "vendor"
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


def run(args: list[str | Path], *, timeout: float | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(a) for a in args],
        capture_output=True,
        timeout=timeout,
        creationflags=NO_WINDOW,
        check=False,
    )


def popen(args: list[str | Path]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [str(a) for a in args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=NO_WINDOW,
    )
