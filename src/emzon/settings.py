"""Preferences that survive a restart."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QByteArray, QSettings

from emzon.export.jobs import AudioFormat

ORGANIZATION = "Metessi"
APPLICATION = "Emzon"


@dataclass
class Preferences:
    export_folder: Path | None = None
    replace_original: bool = False
    audio_format: AudioFormat = AudioFormat.MP3


def _store() -> QSettings:
    return QSettings(ORGANIZATION, APPLICATION)


def load() -> Preferences:
    store = _store()
    folder = store.value("export/folder", "", str)
    try:
        audio_format = AudioFormat(store.value("export/audio_format", AudioFormat.MP3.value, str))
    except ValueError:
        audio_format = AudioFormat.MP3
    return Preferences(
        export_folder=Path(folder) if folder else None,
        replace_original=store.value("export/replace_original", False, bool),
        audio_format=audio_format,
    )


def save(preferences: Preferences) -> None:
    store = _store()
    store.setValue("export/folder", str(preferences.export_folder) if preferences.export_folder else "")
    store.setValue("export/replace_original", preferences.replace_original)
    store.setValue("export/audio_format", preferences.audio_format.value)
    store.sync()


def window_geometry() -> QByteArray:
    value = _store().value("window/geometry")
    return value if isinstance(value, QByteArray) else QByteArray()


def save_window_geometry(geometry: QByteArray) -> None:
    store = _store()
    store.setValue("window/geometry", geometry)
    store.sync()
