"""Preferences, applied as soon as they change."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from emzon import settings
from emzon.export.jobs import AudioFormat
from emzon.ui import strings, theme
from emzon.ui.widgets import IconButton


class Segmented(QWidget):
    """A row of mutually exclusive choices."""

    changed = Signal(int)

    def __init__(self, labels: Sequence[str], tooltips: Sequence[str] = (), parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("segmented")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setStyleSheet(
            f"""
            QWidget#segmented {{ background: {theme.BG.name()}; border: 1px solid {theme.LINE.name()}; border-radius: 10px; }}
            QPushButton {{ border: none; border-radius: 8px; min-height: 32px; padding: 0 14px; color: {theme.MUTED.name()}; }}
            QPushButton:hover {{ color: {theme.TEXT.name()}; background: {theme.RAISED.name()}; }}
            QPushButton:checked {{ background: {theme.ACCENT.name()}; color: #120E1A; }}
            """
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(3, 3, 3, 3)
        row.setSpacing(2)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        for index, label in enumerate(labels):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            if index < len(tooltips) and tooltips[index]:
                button.setToolTip(tooltips[index])
            self.group.addButton(button, index)
            row.addWidget(button)
        self.group.idClicked.connect(self.changed)

    def select(self, index: int) -> None:
        self.group.button(index).setChecked(True)

    @property
    def selected(self) -> int:
        return self.group.checkedId()


class SettingsDialog(QDialog):
    changed = Signal(object)

    def __init__(self, preferences: settings.Preferences, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.preferences = preferences
        self.setWindowTitle(strings.SETTINGS)
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setStyleSheet(f"QDialog {{ background: {theme.PANEL.name()}; }}")

        column = QVBoxLayout(self)
        column.setContentsMargins(28, 20, 20, 28)
        column.setSpacing(10)

        top = QHBoxLayout()
        title = QLabel(strings.SETTINGS)
        title.setFont(theme.ui_font(18, QFont.Weight.DemiBold))
        close = IconButton("close", strings.CLOSE)
        close.clicked.connect(self.accept)
        top.addWidget(title, 1)
        top.addWidget(close)
        column.addLayout(top)
        column.addSpacing(8)

        self.destination = Segmented([strings.DESTINATION_BESIDE, strings.DESTINATION_FOLDER])
        self.destination.changed.connect(self._destination_changed)
        self.folder_label = QLabel()
        self.folder_label.setStyleSheet(f"color: {theme.MUTED.name()};")
        self.folder_label.setFont(theme.mono_font(12))
        self.choose = QPushButton(strings.CHOOSE_FOLDER)
        self.choose.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.choose.setCursor(Qt.CursorShape.PointingHandCursor)
        self.choose.clicked.connect(self._choose_folder)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder_label, 1)
        folder_row.addWidget(self.choose)
        self.folder_row = QWidget()
        self.folder_row.setLayout(folder_row)
        folder_row.setContentsMargins(0, 0, 0, 0)
        self._section(column, strings.DESTINATION, self.destination)
        column.addWidget(self.folder_row)

        self.mode = Segmented([strings.VIDEO_SAVE_COPY, strings.VIDEO_SAVE_REPLACE], ["", strings.VIDEO_SAVE_REPLACE_TIP])
        self.mode.changed.connect(self._mode_changed)
        self._section(column, strings.VIDEO_SAVE, self.mode)

        self.formats = list(AudioFormat)
        self.audio = Segmented([f.value.upper() for f in self.formats])
        self.audio.changed.connect(self._audio_changed)
        self._section(column, strings.AUDIO_FORMAT, self.audio)

        QShortcut(QKeySequence("Esc"), self, activated=self.accept)
        self._show()

    def _section(self, column: QVBoxLayout, title: str, control: QWidget) -> None:
        column.addSpacing(10)
        label = QLabel(title)
        label.setFont(theme.ui_font(13, QFont.Weight.Medium))
        label.setStyleSheet(f"color: {theme.MUTED.name()};")
        column.addWidget(label)
        column.addWidget(control, 0, Qt.AlignmentFlag.AlignLeft)

    def _show(self) -> None:
        p = self.preferences
        self.destination.select(1 if p.export_folder else 0)
        self.folder_row.setVisible(p.export_folder is not None)
        if p.export_folder:
            self.folder_label.setText(self.fontMetrics().elidedText(str(p.export_folder), Qt.TextElideMode.ElideMiddle, 320))
            self.folder_label.setToolTip(str(p.export_folder))
        self.mode.select(1 if p.replace_original else 0)
        self.audio.select(self.formats.index(p.audio_format))

    def _commit(self) -> None:
        settings.save(self.preferences)
        self.changed.emit(self.preferences)
        self._show()

    def _destination_changed(self, index: int) -> None:
        if index == 1 and self.preferences.export_folder is None:
            if not self._choose_folder():
                self._show()
            return
        if index == 0:
            self.preferences.export_folder = None
            self._commit()

    def _choose_folder(self) -> bool:
        start = str(self.preferences.export_folder or Path.home())
        folder = QFileDialog.getExistingDirectory(self, strings.CHOOSE_FOLDER_DIALOG, start)
        if not folder:
            return False
        self.preferences.export_folder = Path(folder)
        self._commit()
        return True

    def _mode_changed(self, index: int) -> None:
        self.preferences.replace_original = index == 1
        self._commit()

    def _audio_changed(self, index: int) -> None:
        self.preferences.audio_format = self.formats[index]
        self._commit()
