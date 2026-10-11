"""The clips of the current folder, beside the video, with the open clip's details."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QModelIndex, QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QFont, QImage, QPainter, QPainterPath, QPen
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
from emzon.media.thumbnails import Thumbnails
from emzon.timefmt import format_length
from emzon.ui import strings, theme
from emzon.units import codec_name, format_fps, format_size

WIDTH = 360
TILE_W = 156
TILE_H = 142
THUMB_H = 82
SLIDE_MS = 180
PATH_ROLE = Qt.ItemDataRole.UserRole
DETAIL_ROLE = Qt.ItemDataRole.UserRole + 1
CLIP_ROLE = Qt.ItemDataRole.UserRole + 2


class ClipTiles(QStyledItemDelegate):
    """A clip as a tile: a frame from it, its name, its length and size."""

    def __init__(self, thumbnails: Thumbnails | None, parent=None) -> None:
        super().__init__(parent)
        self.thumbnails = thumbnails

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(TILE_W, TILE_H)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tile = QRectF(option.rect).adjusted(4, 4, -4, -4)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        if hovered and not selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(theme.RAISED)
            painter.drawRoundedRect(tile.adjusted(-2, -2, 2, 2), 10, 10)

        thumb = QRectF(tile.left(), tile.top(), tile.width(), THUMB_H)
        shape = QPainterPath()
        shape.addRoundedRect(thumb, 8, 8)
        painter.fillPath(shape, theme.LANE)
        image = self._frame(index)
        if image is not None:
            painter.save()
            painter.setClipPath(shape)
            source_w = min(image.width(), image.height() * thumb.width() / thumb.height())
            source_h = min(image.height(), image.width() * thumb.height() / thumb.width())
            source = QRectF((image.width() - source_w) / 2, (image.height() - source_h) / 2, source_w, source_h)
            painter.drawImage(thumb, image, source)
            painter.restore()
        if selected:
            painter.setPen(QPen(theme.ACCENT, 2.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(thumb.adjusted(1, 1, -1, -1), 7, 7)

        name = index.data(Qt.ItemDataRole.DisplayRole)
        painter.setFont(theme.ui_font(12, QFont.Weight.Medium))
        painter.setPen(theme.TEXT if selected else theme.TEXT.darker(112))
        line = QRectF(tile.left() + 2, thumb.bottom() + 6, tile.width() - 4, 18)
        painter.drawText(line, Qt.AlignmentFlag.AlignVCenter, painter.fontMetrics().elidedText(name, Qt.TextElideMode.ElideMiddle, int(line.width())))
        painter.setFont(theme.mono_font(11))
        painter.setPen(theme.MUTED)
        painter.drawText(line.translated(0, 18), Qt.AlignmentFlag.AlignVCenter, index.data(DETAIL_ROLE) or "")
        painter.restore()

    def _frame(self, index: QModelIndex) -> QImage | None:
        clip = index.data(CLIP_ROLE)
        if self.thumbnails is None or clip is None:
            return None
        return self.thumbnails.get(clip.path, frame_time(clip.duration), False)


def frame_time(duration: float) -> float:
    """Where a clip's tile takes its frame: late in the clip, where the action usually is."""
    return round(max(0.0, duration * 0.75), 1)


class FolderPanel(QWidget):
    open_requested = Signal(Path)

    def __init__(self, thumbnails: Thumbnails | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("folder")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setStyleSheet(f"QWidget#folder {{ background: {theme.PANEL.name()}; border-right: 1px solid {theme.LINE.name()}; }}")
        self.is_open = False
        self.setFixedWidth(0)
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(SLIDE_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.valueChanged.connect(lambda width: self.setFixedWidth(int(width)))

        column = QVBoxLayout(self)
        column.setContentsMargins(14, 16, 6, 8)
        column.setSpacing(10)

        self._details_box = QWidget()
        self._details = QGridLayout(self._details_box)
        self._details.setContentsMargins(0, 0, 0, 0)
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
        self._details_box.hide()
        column.addWidget(self._details_box)
        column.addSpacing(10)

        self._list_title = QLabel()
        self._list_title.setFont(theme.ui_font(12, QFont.Weight.Medium))
        self._list_title.setStyleSheet(f"color: {theme.MUTED.name()};")
        column.addWidget(self._list_title)

        self.list = QListWidget()
        self.list.setItemDelegate(ClipTiles(thumbnails, self.list))
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setMovement(QListWidget.Movement.Static)
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setWrapping(True)
        self.list.setGridSize(QSize(TILE_W, TILE_H))
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
            self.setFixedWidth(target)
            return
        self._animation.stop()
        self._animation.setStartValue(self.width())
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
        item.setData(CLIP_ROLE, clip)
        parts = []
        if clip is not None:
            parts.append(format_length(clip.duration))
        if size is not None:
            parts.append(format_size(size))
        item.setData(DETAIL_ROLE, "    ".join(parts))

    def show_clip(self, clip: Clip | None) -> None:
        self._details_box.setVisible(clip is not None)
        if clip is None:
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
