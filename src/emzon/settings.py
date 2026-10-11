"""Preferences that survive a restart."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QByteArray, QSettings, QStandardPaths

from emzon.export.jobs import AudioFormat

ORGANIZATION = "Metessi"
APPLICATION = "Emzon"


@dataclass
class Preferences:
    export_folder: Path | None = None
    replace_original: bool = False
    audio_format: AudioFormat = AudioFormat.MP3
    preview_scale: int = 1
    folder_panel: bool = False
    last_folder: Path | None = None


PREVIEW_SCALES = (1, 2)


def _store() -> QSettings:
    return QSettings(ORGANIZATION, APPLICATION)


def load() -> Preferences:
    store = _store()
    folder = store.value("export/folder", "", str)
    try:
        audio_format = AudioFormat(store.value("export/audio_format", AudioFormat.MP3.value, str))
    except ValueError:
        audio_format = AudioFormat.MP3
    scale = store.value("preview/scale", 1, int)
    return Preferences(
        export_folder=Path(folder) if folder else None,
        replace_original=store.value("export/replace_original", False, bool),
        audio_format=audio_format,
        preview_scale=scale if scale in PREVIEW_SCALES else 1,
        folder_panel=store.value("window/folder_panel", False, bool),
        last_folder=Path(last) if (last := store.value("history/last_folder", "", str)) else None,
    )


def save(preferences: Preferences) -> None:
    store = _store()
    store.setValue("export/folder", str(preferences.export_folder) if preferences.export_folder else "")
    store.setValue("export/replace_original", preferences.replace_original)
    store.setValue("export/audio_format", preferences.audio_format.value)
    store.setValue("preview/scale", preferences.preview_scale)
    store.setValue("window/folder_panel", preferences.folder_panel)
    store.setValue("history/last_folder", str(preferences.last_folder) if preferences.last_folder else "")
    store.sync()


def window_geometry() -> QByteArray:
    value = _store().value("window/geometry")
    return value if isinstance(value, QByteArray) else QByteArray()


def save_window_geometry(geometry: QByteArray) -> None:
    store = _store()
    store.setValue("window/geometry", geometry)
    store.sync()


def videos_folder() -> Path:
    return Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.MoviesLocation))


def dialog_start(last_folder: Path | None, videos: Path) -> Path:
    """Where the open dialogs start: the last folder used if it still exists, else the system Videos folder."""
    if last_folder is not None and last_folder.is_dir():
        return last_folder
    if videos.is_dir():
        return videos
    return Path.home()
