"""The clips of the current folder, beside the video, with the open clip's details."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QModelIndex, QPropertyAnimation, QRect, QSize, Qt, Signal
from PySide6.QtGui import QFont, QPainter
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

from emzon.media.probe import Clip
from emzon.timefmt import format_length
from emzon.ui import strings, theme
from emzon.units import codec_name, format_fps, format_size

WIDTH = 300
ROW_HEIGHT = 52
SLIDE_MS = 180
PATH_ROLE = Qt.ItemDataRole.UserRole
DETAIL_ROLE = Qt.ItemDataRole.UserRole + 1


class ClipRows(QStyledItemDelegate):
    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(0, ROW_HEIGHT)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = option.rect.adjusted(8, 2, -8, -2)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        if selected:
            tint = theme.ACCENT.lighter(100)
            tint.setAlpha(46)
            painter.setBrush(tint)
        elif hovered:
            painter.setBrush(theme.RAISED)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 8, 8)
        if selected:
            painter.setBrush(theme.ACCENT)
            painter.drawRoundedRect(rect.adjusted(0, 8, -(rect.width() - 3), -8), 1.5, 1.5)

        name = index.data(Qt.ItemDataRole.DisplayRole)
        painter.setFont(theme.ui_font(13, QFont.Weight.Medium))
        painter.setPen(theme.TEXT if selected else theme.TEXT.darker(108))
        text_rect = QRect(rect.left() + 12, rect.top() + 7, rect.width() - 20, 18)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, painter.fontMetrics().elidedText(name, Qt.TextElideMode.ElideMiddle, text_rect.width()))
        detail = index.data(DETAIL_ROLE) or ""
        painter.setFont(theme.mono_font(11))
        painter.setPen(theme.MUTED)
        painter.drawText(QRect(rect.left() + 12, rect.top() + 26, rect.width() - 20, 16), Qt.AlignmentFlag.AlignVCenter, detail)
        painter.restore()


class FolderPanel(QWidget):
    open_requested = Signal(Path)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("folder")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setStyleSheet(f"QWidget#folder {{ background: {theme.PANEL.name()}; border-right: 1px solid {theme.LINE.name()}; }}")
        self.is_open = False
        self.setMaximumWidth(0)
        self.setMinimumWidth(0)
        self._animation = QPropertyAnimation(self, b"maximumWidth", self)
        self._animation.setDuration(SLIDE_MS)

        column = QVBoxLayout(self)
        column.setContentsMargins(16, 16, 8, 8)
        column.setSpacing(10)

        self._details = QGridLayout()
        self._details.setHorizontalSpacing(14)
        self._details.setVerticalSpacing(6)
        self._values: dict[str, QLabel] = {}
        for row, key in enumerate(strings.DETAIL_LABELS):
            label = QLabel(strings.DETAIL_LABELS[key])
            label.setStyleSheet(f"color: {theme.MUTED.name()};")
            value = QLabel()
            value.setFont(theme.mono_font(12))
            self._details.addWidget(label, row, 0)
            self._details.addWidget(value, row, 1)
            self._values[key] = value
        self._details.setColumnStretch(1, 1)
        column.addLayout(self._details)
        column.addSpacing(10)

        self._list_title = QLabel()
        self._list_title.setFont(theme.ui_font(12, QFont.Weight.Medium))
        self._list_title.setStyleSheet(f"color: {theme.MUTED.name()};")
        column.addWidget(self._list_title)

        self.list = QListWidget()
        self.list.setItemDelegate(ClipRows(self.list))
        self.list.setMouseTracking(True)
        self.list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list.setUniformItemSizes(True)
        self.list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setStyleSheet("QListWidget { background: transparent; border: none; outline: none; }")
        self.list.itemClicked.connect(lambda item: self.open_requested.emit(item.data(PATH_ROLE)))
        column.addWidget(self.list, 1)
        self._items: dict[Path, QListWidgetItem] = {}

    def set_open(self, open_: bool, animated: bool = True) -> None:
        self.is_open = open_
        target = WIDTH if open_ else 0
        if not animated:
            self._animation.stop()
            self.setMaximumWidth(target)
            return
        self._animation.stop()
        self._animation.setStartValue(self.maximumWidth())
        self._animation.setEndValue(target)
        self._animation.start()

    def set_clips(self, files: list[Path], current: Path | None) -> None:
        if list(self._items) != files:
            self.list.clear()
            self._items = {}
            for path in files:
                item = QListWidgetItem(path.name)
                item.setData(PATH_ROLE, path)
                self.list.addItem(item)
                self._items[path] = item
        self._list_title.setText(strings.FOLDER_COUNT.format(count=len(files)))
        item = self._items.get(current) if current else None
        if item is not None:
            self.list.setCurrentItem(item)
            self.list.scrollToItem(item)
        else:
            self.list.clearSelection()

    def set_detail(self, path: Path, clip: Clip | None, size: int | None) -> None:
        item = self._items.get(path)
        if item is None:
            return
        parts = []
        if clip is not None:
            parts.append(format_length(clip.duration))
        if size is not None:
            parts.append(format_size(size))
        item.setData(DETAIL_ROLE, "    ".join(parts))

    def show_clip(self, clip: Clip | None) -> None:
        if clip is None:
            for value in self._values.values():
                value.setText("")
            return
        try:
            info = clip.path.stat()
            size, modified = format_size(info.st_size), datetime.fromtimestamp(info.st_mtime).strftime("%d/%m/%Y %H:%M")
        except OSError:
            size, modified = "?", "?"
        values = {
            "length": format_length(clip.duration),
            "resolution": f"{clip.width}×{clip.height}",
            "fps": format_fps(clip.fps),
            "codec": codec_name(clip.video_codec),
            "audio": str(len(clip.audio)),
            "size": size,
            "date": modified,
        }
        for key, value in values.items():
            self._values[key].setText(value)
