"""Stroke icons, drawn in any colour at any scale."""

from __future__ import annotations

from functools import cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_STROKE = '<g fill="none" stroke="{color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">{body}</g>'
_FILL = '<g fill="{color}" stroke="none">{body}</g>'

ICONS = {
    "folder": (_STROKE, '<path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>'),
    "play": (_FILL, '<path d="M8 5v14l11-7z"/>'),
    "pause": (_FILL, '<rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/>'),
    "cut-head": (_STROKE, '<path d="M9 4H6v16h3"/><path d="M14 12h6M17 9l3 3-3 3"/>'),
    "cut-tail": (_STROKE, '<path d="M15 4h3v16h-3"/><path d="M10 12H4M7 9l-3 3 3 3"/>'),
    "zoom": (_STROKE, '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/>'),
    "speaker": (_STROKE, '<path d="M11 5L6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 010 7"/>'),
    "speaker-off": (_STROKE, '<path d="M11 5L6 9H3v6h3l5 4z"/><path d="M16 9l5 6M21 9l-5 6"/>'),
    "chevron-left": (_STROKE, '<path d="M15 18l-6-6 6-6"/>'),
    "chevron-right": (_STROKE, '<path d="M9 18l6-6-6-6"/>'),
    "settings": (_STROKE, '<path d="M18.97 10.20 L21.47 10.42 L21.47 13.58 L18.97 13.80 L18.20 15.66 L19.81 17.58 L17.58 19.81 L15.66 18.20 L13.80 18.97 L13.58 21.47 L10.42 21.47 L10.20 18.97 L8.34 18.20 L6.42 19.81 L4.19 17.58 L5.80 15.66 L5.03 13.80 L2.53 13.58 L2.53 10.42 L5.03 10.20 L5.80 8.34 L4.19 6.42 L6.42 4.19 L8.34 5.80 L10.20 5.03 L10.42 2.53 L13.58 2.53 L13.80 5.03 L15.66 5.80 L17.58 4.19 L19.81 6.42 L18.20 8.34Z"/><circle cx="12" cy="12" r="3.2"/>'),
    "folder-open": (_STROKE, '<path d="M3 17V7a2 2 0 012-2h4l2 2h7a2 2 0 012 2v1"/><path d="M3 17l2.4-6.2A1.5 1.5 0 016.8 10H21l-2.6 7.2A1.5 1.5 0 0117 18.2H4a1 1 0 01-1-1.2z"/>'),
    "file": (_STROKE, '<path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8z"/><path d="M14 3v5h5"/>'),
    "history": (_STROKE, '<path d="M3 12a9 9 0 103-6.7"/><path d="M3 4v4h4"/><path d="M12 8v4l3 2"/>'),
    "gauge": (_STROKE, '<path d="M4 16a8 8 0 1116 0"/><path d="M12 16l4-5"/>'),
    "sidebar": (_STROKE, '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/>'),
    "sliders": (_STROKE, '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>'),
    "wave": (_STROKE, '<path d="M3 12h2M7 8v8M11 5v14M15 9v6M19 11v2"/>'),
    "film": (_STROKE, '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 5v14M17 5v14"/>'),
    "check": (_STROKE, '<path d="M5 12l5 5 9-10"/>'),
    "close": (_STROKE, '<path d="M6 6l12 12M18 6L6 18"/>'),
    "clock": (_STROKE, '<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>'),
    "alert": (_STROKE, '<circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 16.5v.5"/>'),
}


def _svg(name: str, color: QColor) -> bytes:
    template, body = ICONS[name]
    group = template.format(color=color.name(), body=body)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{group}</svg>'.encode()


@cache
def _renderer(name: str, color: str) -> QSvgRenderer:
    return QSvgRenderer(QByteArray(_svg(name, QColor(color))))


def paint(painter: QPainter, name: str, rect: QRectF, color: QColor) -> None:
    _renderer(name, color.name()).render(painter, rect)


def icon(name: str, color: QColor, size: int = 20, ratio: float = 2.0) -> QIcon:
    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    paint(painter, name, QRectF(0, 0, pixmap.width(), pixmap.height()), color)
    painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return QIcon(pixmap)
