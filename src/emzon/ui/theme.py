"""Design tokens. Values mirror docs/design.md."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette

BG = QColor("#0E0C13")
PANEL = QColor("#14111B")
LANE = QColor("#1A1622")
RAISED = QColor("#1E1A28")
LINE = QColor("#2A2535")
LINE_STRONG = QColor("#6B5F8A")
TEXT = QColor("#ECE8F4")
MUTED = QColor("#9A93AB")
FAINT = QColor("#7E7791")
ACCENT = QColor("#9B7BFF")
ACCENT_SOFT = QColor("#B9A4FF")
ON_ACCENT = QColor("#120E1A")
OK = QColor("#8FE3B0")
ERROR = QColor("#FF8A9A")

TRACK_COLORS = [QColor("#A88BFF"), QColor("#D9CCFF"), QColor("#8E6CF0"), QColor("#C4B1FF")]

UI_FAMILY = "Geist"
MONO_FAMILY = "Geist Mono"

FONTS_DIR = Path(__file__).with_name("fonts")


def track_color(position: int) -> QColor:
    return TRACK_COLORS[position % len(TRACK_COLORS)]


def load_fonts() -> None:
    for file in ("Geist-Variable.ttf", "GeistMono-Variable.ttf"):
        QFontDatabase.addApplicationFont(str(FONTS_DIR / file))


def palette() -> QPalette:
    """Dark colours for everything Qt draws itself, dialogs included."""
    p = QPalette()
    roles = {
        QPalette.ColorRole.Window: PANEL,
        QPalette.ColorRole.WindowText: TEXT,
        QPalette.ColorRole.Base: LANE,
        QPalette.ColorRole.AlternateBase: RAISED,
        QPalette.ColorRole.Text: TEXT,
        QPalette.ColorRole.Button: RAISED,
        QPalette.ColorRole.ButtonText: TEXT,
        QPalette.ColorRole.Highlight: ACCENT,
        QPalette.ColorRole.HighlightedText: ON_ACCENT,
        QPalette.ColorRole.ToolTipBase: LANE,
        QPalette.ColorRole.ToolTipText: TEXT,
        QPalette.ColorRole.PlaceholderText: FAINT,
        QPalette.ColorRole.Link: ACCENT_SOFT,
    }
    for role, color in roles.items():
        p.setColor(role, color)
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        p.setColor(QPalette.ColorGroup.Disabled, role, FAINT)
    return p


def ui_font(pixel_size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont(UI_FAMILY)
    font.setPixelSize(pixel_size)
    font.setWeight(weight)
    return font


def mono_font(pixel_size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont(MONO_FAMILY)
    font.setPixelSize(pixel_size)
    font.setWeight(weight)
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font


STYLESHEET = f"""
QMainWindow {{ background: {BG.name()}; }}
QWidget {{ color: {TEXT.name()}; }}
QWidget#panel {{ background: {PANEL.name()}; }}
QToolTip {{
    background: {LANE.name()};
    color: {TEXT.name()};
    border: 1px solid {LINE.name()};
    padding: 6px 8px;
}}
QPushButton {{
    background: transparent;
    border: 1px solid #3A3348;
    border-radius: 10px;
    padding: 0 14px;
    min-height: 38px;
    font-size: 14px;
    font-weight: 500;
}}
QPushButton:hover {{ background: {RAISED.name()}; }}
QPushButton:disabled {{ color: {FAINT.name()}; border-color: {LINE.name()}; }}
QPushButton[role="primary"] {{
    background: {ACCENT.name()};
    color: {ON_ACCENT.name()};
    border: none;
    font-weight: 600;
}}
QPushButton[role="primary"]:hover {{ background: #AC92FF; }}
QPushButton[role="primary"]:disabled {{ background: {LINE.name()}; color: {FAINT.name()}; }}
QPushButton[role="icon"] {{
    border: none;
    border-radius: 10px;
    padding: 0;
    min-height: 36px;
    min-width: 36px;
}}
QPushButton[role="play"] {{
    background: {TEXT.name()};
    border: none;
    border-radius: 22px;
    min-height: 44px;
    min-width: 44px;
    padding: 0;
}}
QPushButton[role="play"]:hover {{ background: #FFFFFF; }}
QLabel {{ background: transparent; }}
"""
