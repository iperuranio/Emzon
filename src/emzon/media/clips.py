"""The clips of a folder, newest first."""

from __future__ import annotations

from pathlib import Path

from emzon.export.jobs import PARTIAL_SUFFIX

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".m4v", ".webm", ".avi"}


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS and not path.stem.endswith(PARTIAL_SUFFIX)


def clips_in(folder: Path) -> list[Path]:
    try:
        entries = [p for p in folder.iterdir() if p.is_file() and is_video(p)]
    except OSError:
        return []
    return sorted(entries, key=lambda p: (-_modified(p), p.name.lower()))


def _modified(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


class Playlist:
    def __init__(self, files: list[Path], index: int = 0) -> None:
        if not files:
            raise ValueError("a playlist needs at least one clip")
        self.files = files
        self.index = min(max(index, 0), len(files) - 1)

    @classmethod
    def around(cls, path: Path) -> Playlist:
        """The clip's folder, positioned on the clip."""
        files = clips_in(path.parent)
        if path not in files:
            files.insert(0, path)
        return cls(files, files.index(path))

    @classmethod
    def of_folder(cls, folder: Path) -> Playlist | None:
        files = clips_in(folder)
        return cls(files) if files else None

    @property
    def current(self) -> Path:
        return self.files[self.index]

    def step(self, delta: int) -> Path | None:
        target = self.index + delta
        if not 0 <= target < len(self.files):
            return None
        self.index = target
        return self.current

    @property
    def position(self) -> str:
        return f"{self.index + 1}/{len(self.files)}"
