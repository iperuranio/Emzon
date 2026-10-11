"""Lighter copies of a clip for smooth playback and scrubbing.

A preview copy is scaled down and made of keyframes only, so any frame decodes
on its own; the audio tracks are copied unchanged. Exports never use it.
"""

from __future__ import annotations

import hashlib
import logging
import os
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from emzon.export.jobs import parse_progress
from emzon.media.tools import Stream, find_tool

log = logging.getLogger(__name__)

GROUP = "proxy"
CACHE_LIMIT = 3 * 1024**3
SUFFIX = ".mkv"
ERROR_LINES = 3

HARDWARE = ["-c:v", "h264_nvenc", "-preset", "p1", "-g", "1", "-bf", "0", "-rc", "vbr", "-cq", "28", "-b:v", "0"]
SOFTWARE = ["-c:v", "libx264", "-preset", "ultrafast", "-tune", "fastdecode", "-g", "1", "-crf", "26"]


class ProxyError(RuntimeError):
    pass


def cache_dir() -> Path:
    base = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation))
    return base / "previews"


def proxy_path(source: Path, scale: int, folder: Path | None = None) -> Path:
    """Named after the clip's path, size, date and scale, so a changed clip gets a new copy."""
    info = source.stat()
    key = f"{source.resolve()}|{info.st_size}|{info.st_mtime_ns}|{scale}"
    return (folder or cache_dir()) / (hashlib.sha1(key.encode()).hexdigest()[:24] + SUFFIX)


def existing(source: Path, scale: int, folder: Path | None = None) -> Path | None:
    path = proxy_path(source, scale, folder)
    if not path.is_file():
        return None
    os.utime(path)
    return path


def command(source: Path, scale: int, target: Path, hardware: bool) -> list[str]:
    return [
        str(find_tool("ffmpeg")), "-hide_banner", "-nostdin", "-y", "-v", "error",
        "-progress", "pipe:1", "-nostats",
        "-i", str(source),
        "-map", "0:v:0", "-map", "0:a?",
        "-vf", f"scale=trunc(iw/{scale}/2)*2:-2",
        *(HARDWARE if hardware else SOFTWARE),
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        str(target),
    ]


def build(
    source: Path, scale: int, duration: float, progress: Callable[[float], None], folder: Path | None = None
) -> Path:
    """Write the preview copy, trying NVENC first, and return its path."""
    target = proxy_path(source, scale, folder)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.stem + ".partial" + SUFFIX)
    errors: list[str] = []
    for hardware in (True, False):
        errors = []
        with Stream(command(source, scale, partial, hardware), group=GROUP) as process:
            for raw in process.stdout:
                line = raw.decode(errors="replace")
                fraction = parse_progress(line, duration)
                if fraction is not None:
                    progress(fraction)
            errors = process.stderr.read().decode(errors="replace").strip().splitlines()
            code = process.wait()
        if code == 0:
            os.replace(partial, target)
            prune(folder or cache_dir(), keep=target)
            return target
        if hardware:
            log.info("preview copy without NVENC: %s", errors[-ERROR_LINES:])
    partial.unlink(missing_ok=True)
    raise ProxyError("\n".join(errors[-ERROR_LINES:]) or "ffmpeg failed")


def prune(folder: Path, keep: Path, limit: int = CACHE_LIMIT) -> None:
    """Delete the least recently used copies until the cache fits the limit."""
    copies = sorted(
        (p for p in folder.glob(f"*{SUFFIX}") if p != keep and ".partial" not in p.name),
        key=lambda p: p.stat().st_mtime,
    )
    total = sum(p.stat().st_size for p in copies) + (keep.stat().st_size if keep.exists() else 0)
    for path in copies:
        if total <= limit:
            break
        total -= path.stat().st_size
        path.unlink(missing_ok=True)
