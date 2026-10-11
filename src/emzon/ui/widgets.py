"""Small controls shared by the window."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QLabel, QPushButton, QSizePolicy, QWidget

from emzon.ui import icons, theme

KEYCAP_GAP = 10


class ActionButton(QPushButton):
    """A button that shows its keyboard shortcut as a key cap."""

    def __init__(
        self, text: str, icon_name: str, key: str, tooltip: str, primary: bool = False, parent: QWidget | None = None
    ) -> None:
        super().__init__(text, parent)
        self.key = key
        self.primary = primary
        if primary:
            self.setProperty("role", "primary")
        self.setIcon(icons.icon(icon_name, theme.ON_ACCENT if primary else theme.TEXT, 18))
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
        if not self.isEnabled():
            color = theme.LINE
        else:
            color = theme.ON_ACCENT if self.primary else theme.MUTED
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


class DropOverlay(QWidget):
    """A violet frame over the window while a file is dragged onto it."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tint = QColor(theme.ACCENT)
        tint.setAlpha(28)
        painter.fillRect(self.rect(), tint)
        painter.setPen(QPen(theme.ACCENT, 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(8, 8, -8, -8), 16, 16)


class ElidedLabel(QLabel):
    """A one-line label that shortens long text in the middle instead of widening the window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def setText(self, text: str) -> None:
        self._full = text
        self.setToolTip(text)
        self._elide()

    def text(self) -> str:
        return self._full

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._elide()

    def _elide(self) -> None:
        super().setText(self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideMiddle, max(0, self.width())))
