"""Small controls shared by the window."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QFontMetrics, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QPushButton, QWidget

from emzon.ui import icons, theme

KEYCAP_GAP = 10


class ActionButton(QPushButton):
    """A button that shows its keyboard shortcut as a key cap."""

    def __init__(self, text: str, icon_name: str, key: str, tooltip: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.key = key
        self.setIcon(icons.icon(icon_name, theme.TEXT, 18))
        self.setIconSize(QSize(18, 18))
        self.setToolTip(tooltip)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        keycap = QFontMetrics(theme.mono_font(11)).horizontalAdvance(key) + 12
        self.setStyleSheet(f"padding-right: {keycap + 2 * KEYCAP_GAP}px;")

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(theme.mono_font(11))
        width = painter.fontMetrics().horizontalAdvance(self.key) + 12
        rect = QRectF(self.width() - KEYCAP_GAP - width, (self.height() - 20) / 2, width, 20)
        color = theme.MUTED if self.isEnabled() else theme.LINE
        painter.setPen(QPen(color, 1))
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 5, 5)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.key)


class IconButton(QPushButton):
    def __init__(self, icon_name: str, tooltip: str, parent: QWidget | None = None, size: int = 20) -> None:
        super().__init__(parent)
        self.setProperty("role", "icon")
        self.setIcon(icons.icon(icon_name, theme.MUTED, size))
        self.setIconSize(QSize(size, size))
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class PlayButton(QPushButton):
    def __init__(self, tooltip: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "play")
        self.setToolTip(tooltip)
        self.setIconSize(QSize(16, 16))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_playing(False)

    def show_playing(self, playing: bool) -> None:
        self.setIcon(icons.icon("pause" if playing else "play", theme.BG, 16))
