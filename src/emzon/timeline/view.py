"""The timeline panel: overview, zoom funnel, ruler, one lane per audio track."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PySide6.QtCore import QLineF, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPixmap,
    QPolygonF,
    QWheelEvent,
)
from PySide6.QtWidgets import QWidget

from emzon.media.thumbnails import Thumbnails
from emzon.media.waveform import Waveform
from emzon.timefmt import format_span, format_time
from emzon.timeline.model import END_MARGIN, Timeline
from emzon.ui import icons, strings, theme

PAD_X = 24
PAD_TOP = 12
PAD_BOTTOM = 8
GUTTER = 150
GUTTER_GAP = 12
OVERVIEW_H = 28
FUNNEL_H = 18
RULER_H = 24
VIDEO_H = 48
LANE_H = 64
LANE_GAP = 6
TILE_STEPS = (0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300)
ACCURATE_TILES_BELOW = 4.0
BAR_STEP = 3
MAX_GAIN = 1.5
WHEEL_ZOOM = 0.25
WHEEL_PAN = 0.1
TICK_STEPS = (0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600)
MAX_TICKS = 10


@dataclass
class Track:
    name: str
    gain: float = 1.0
    muted: bool = False
    waveform: Waveform | None = None
    failed: bool = False


class TimelineView(QWidget):
    playhead_requested = Signal(float)
    scrub_started = Signal()
    scrub_finished = Signal()
    gain_changed = Signal(int, float)
    mute_toggled = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.model: Timeline | None = None
        self.tracks: list[Track] = []
        self.path: Path | None = None
        self.thumbnails: Thumbnails | None = None
        self._cache: QPixmap | None = None
        self._drag: str | None = None
        self._drag_track = -1
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_content(self, model: Timeline, tracks: list[Track], path: Path, thumbnails: Thumbnails | None) -> None:
        self.model = model
        self.tracks = tracks
        self.path = path
        self.thumbnails = thumbnails
        self.updateGeometry()
        self.refresh()

    @property
    def scrubbing(self) -> bool:
        return self._drag == "scrub"

    def refresh(self) -> None:
        """Redraw everything; for playhead moves alone, update() is enough."""
        self._cache = None
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(960, self._height())

    def minimumSizeHint(self) -> QSize:
        return QSize(640, self._height())

    def _height(self) -> int:
        return round(self._lanes_bottom()) + PAD_BOTTOM

    # Geometry

    def _content(self) -> tuple[float, float]:
        left = PAD_X + GUTTER + GUTTER_GAP
        return left, self.width() - PAD_X - left

    def _x(self, time: float) -> float:
        left, width = self._content()
        return left + self.model.fraction_of(time) * width

    def _overview(self) -> QRectF:
        left, width = self._content()
        inset = END_MARGIN * width
        return QRectF(left + inset, PAD_TOP, width - 2 * inset, OVERVIEW_H)

    def _ox(self, time: float) -> float:
        rect = self._overview()
        return rect.left() + time / self.model.duration * rect.width()

    def _ruler_top(self) -> float:
        return PAD_TOP + OVERVIEW_H + FUNNEL_H

    def _video_top(self) -> float:
        return self._ruler_top() + RULER_H

    def _lane_top(self, position: int) -> float:
        return self._video_top() + VIDEO_H + LANE_GAP + position * (LANE_H + LANE_GAP)

    def _lanes_bottom(self) -> float:
        return self._lane_top(len(self.tracks)) - LANE_GAP

    def _slider(self, position: int) -> QRectF:
        top = self._lane_top(position) + LANE_H / 2 + 6
        return QRectF(PAD_X + 28, top, GUTTER - 28, 14)

    def _mute(self, position: int) -> QRectF:
        top = self._lane_top(position) + LANE_H / 2 + 2
        return QRectF(PAD_X - 2, top, 22, 22)

    def _file_span(self) -> tuple[float, float]:
        left, width = self._content()
        start = max(left, self._x(0.0))
        end = min(left + width, self._x(self.model.duration))
        return start, end

    # Painting

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        if self.model is None:
            painter.fillRect(self.rect(), theme.PANEL)
            return
        ratio = self.devicePixelRatioF()
        if self._cache is None or self._cache.size() != self.size() * ratio:
            self._cache = QPixmap(self.size() * ratio)
            self._cache.setDevicePixelRatio(ratio)
            self._cache.fill(theme.PANEL)
            static = QPainter(self._cache)
            static.setRenderHint(QPainter.RenderHint.Antialiasing)
            self._paint_static(static)
            static.end()
        painter.drawPixmap(0, 0, self._cache)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_playhead(painter)

    def _paint_static(self, p: QPainter) -> None:
        self._paint_readout(p)
        self._paint_overview(p)
        self._paint_funnel(p)
        self._paint_ruler(p)
        self._paint_video(p)
        for position, track in enumerate(self.tracks):
            self._paint_lane(p, position, track)
            self._paint_gutter(p, position, track)
        self._paint_cuts(p)
        self._paint_edges(p)
        self._paint_handles(p)

    def _paint_readout(self, p: QPainter) -> None:
        y = PAD_TOP + OVERVIEW_H / 2
        icons.paint(p, "zoom", QRectF(PAD_X, y - 8, 16, 16), theme.MUTED)
        span = format_span(self.model.visible_file_span)
        p.setFont(theme.mono_font(13, QFont.Weight.Medium))
        p.setPen(theme.TEXT)
        p.drawText(QPointF(PAD_X + 24, y + 5), span)
        offset = p.fontMetrics().horizontalAdvance(span) + 6
        p.setFont(theme.mono_font(12))
        p.setPen(theme.FAINT)
        p.drawText(QPointF(PAD_X + 24 + offset, y + 5), f"{strings.VIEW_OF} {format_time(self.model.duration, 0)}")

    def _paint_overview(self, p: QPainter) -> None:
        m = self.model
        rect = self._overview()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.LANE)
        p.drawRoundedRect(rect, 6, 6)

        loudest = self._combined_peaks(0.0, m.duration, int(rect.width() / BAR_STEP))
        if loudest is not None:
            self._draw_bars(p, np.sqrt(loudest), rect.adjusted(0, 3, 0, -3), QColor("#4A4160"), 1.4)

        p.save()
        clip = QPainterPath()
        clip.addRoundedRect(rect, 6, 6)
        p.setClipPath(clip)
        if m.head_is_cut:
            self._hatch(p, QRectF(rect.left(), rect.top(), self._ox(m.cut_in) - rect.left(), rect.height()))
        if m.tail_is_cut:
            self._hatch(p, QRectF(self._ox(m.cut_out), rect.top(), rect.right() - self._ox(m.cut_out), rect.height()))
        kept = QColor(theme.ACCENT)
        kept.setAlphaF(0.22)
        p.fillRect(QRectF(self._ox(m.cut_in), rect.top(), self._ox(m.cut_out) - self._ox(m.cut_in), rect.height()), kept)
        p.restore()

        start, end = max(m.view_start, 0.0), min(m.view_end, m.duration)
        frame = QRectF(self._ox(start), rect.top() + 1, max(4.0, self._ox(end) - self._ox(start)), rect.height() - 2)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(0, 0, 0, 100), 3))
        p.drawRoundedRect(frame, 4, 4)
        p.setPen(QPen(theme.TEXT, 2))
        p.drawRoundedRect(frame, 4, 4)

    def _paint_funnel(self, p: QPainter) -> None:
        m = self.model
        top = PAD_TOP + OVERVIEW_H
        start, end = max(m.view_start, 0.0), min(m.view_end, m.duration)
        polygon = QPolygonF([
            QPointF(self._ox(start), top),
            QPointF(self._ox(end), top),
            QPointF(self._x(end), top + FUNNEL_H),
            QPointF(self._x(start), top + FUNNEL_H),
        ])
        p.setBrush(QColor(236, 232, 244, 15))
        p.setPen(QPen(QColor(236, 232, 244, 90), 1))
        p.drawPolygon(polygon)

    def _paint_ruler(self, p: QPainter) -> None:
        m = self.model
        top = self._ruler_top()
        left, width = self._content()
        step = next((s for s in TICK_STEPS if m.span / s <= MAX_TICKS), TICK_STEPS[-1])
        decimals = 2 if step < 0.1 or step == 0.25 else 1 if step < 1 else 0
        p.setFont(theme.mono_font(11))
        handles = [self._x(t) for t, cut in ((m.cut_in, m.head_is_cut), (m.cut_out, m.tail_is_cut)) if cut]
        first = math.ceil(max(m.view_start, 0.0) / step - 1e-9)
        tick = first * step
        while tick < min(m.view_end, m.duration) - 1e-6:
            if tick > 1e-6:
                x = self._x(tick)
                p.setPen(QPen(QColor("#2F2A3B"), 1))
                p.drawLine(QPointF(x, top), QPointF(x, top + RULER_H))
                label = format_time(tick, decimals)
                label_end = x + 6 + p.fontMetrics().horizontalAdvance(label)
                if not any(x - 12 <= h <= label_end + 12 for h in handles):
                    p.setPen(theme.FAINT)
                    p.drawText(QPointF(x + 6, top + 14), label)
            first += 1
            tick = first * step

        p.setFont(theme.ui_font(11, QFont.Weight.DemiBold))
        if m.view_start <= 0:
            x = self._x(0.0)
            p.setPen(QPen(theme.LINE_STRONG, 2))
            p.drawLine(QPointF(x, top), QPointF(x, top + RULER_H))
            p.setPen(theme.MUTED)
            p.drawText(QPointF(x + 8, top + 14), strings.START)
        if m.view_end >= m.duration:
            x = self._x(m.duration)
            p.setPen(QPen(theme.LINE_STRONG, 2))
            p.drawLine(QPointF(x, top), QPointF(x, top + RULER_H))
            p.setPen(theme.MUTED)
            label_width = p.fontMetrics().horizontalAdvance(strings.END)
            p.drawText(QPointF(x - 8 - label_width, top + 14), strings.END)

    def _lane_path(self, rect: QRectF) -> QPainterPath:
        """A lane rounded only at the ends of the file that are in view."""
        m = self.model
        r = 8.0
        left_round = r if m.view_start <= 0 else 0.0
        right_round = r if m.view_end >= m.duration else 0.0
        path = QPainterPath()
        path.moveTo(rect.left() + left_round, rect.top())
        path.lineTo(rect.right() - right_round, rect.top())
        path.arcTo(rect.right() - 2 * right_round, rect.top(), 2 * right_round, 2 * right_round, 90, -90)
        path.lineTo(rect.right(), rect.bottom() - right_round)
        path.arcTo(rect.right() - 2 * right_round, rect.bottom() - 2 * right_round, 2 * right_round, 2 * right_round, 0, -90)
        path.lineTo(rect.left() + left_round, rect.bottom())
        path.arcTo(rect.left(), rect.bottom() - 2 * left_round, 2 * left_round, 2 * left_round, 270, -90)
        path.lineTo(rect.left(), rect.top() + left_round)
        path.arcTo(rect.left(), rect.top(), 2 * left_round, 2 * left_round, 180, -90)
        path.closeSubpath()
        return path

    def _paint_video(self, p: QPainter) -> None:
        m = self.model
        top = self._video_top()
        icons.paint(p, "film", QRectF(PAD_X, top + VIDEO_H / 2 - 8, 16, 16), theme.MUTED)
        p.setFont(theme.ui_font(13))
        p.setPen(theme.MUTED)
        p.drawText(QPointF(PAD_X + 24, top + VIDEO_H / 2 + 5), strings.VIDEO_LANE)

        start, end = self._file_span()
        if end <= start:
            return
        rect = QRectF(start, top, end - start, VIDEO_H)
        path = self._lane_path(rect)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.LANE)
        p.drawPath(path)
        if self.thumbnails is None or self.path is None:
            return

        left, width = self._content()
        tile_width = VIDEO_H * 16 / 9
        seconds_per_pixel = m.span / width
        step = next((s for s in TILE_STEPS if s / seconds_per_pixel >= tile_width), TILE_STEPS[-1])
        accurate = step < ACCURATE_TILES_BELOW
        first = math.floor(max(m.view_start, 0.0) / step)
        last = math.ceil(min(m.view_end, m.duration) / step)
        shown: set[tuple[float, bool]] = set()
        p.save()
        p.setClipPath(path)
        for k in range(first, last):
            t0, t1 = k * step, min((k + 1) * step, m.duration)
            time = round(max(0.0, min(t0 + step / 2, m.duration - 0.05)), 2)
            shown.add((time, accurate))
            image = self.thumbnails.get(self.path, time, accurate)
            if image is None:
                continue
            target = QRectF(self._x(t0) + 1, top, self._x(t1) - self._x(t0) - 2, VIDEO_H)
            source_width = min(image.width(), image.height() * target.width() / target.height())
            source_height = min(image.height(), image.width() * target.height() / target.width())
            source = QRectF((image.width() - source_width) / 2, (image.height() - source_height) / 2, source_width, source_height)
            p.drawImage(target, image, source)
        p.restore()
        self.thumbnails.keep_only(self.path, shown)

    def _paint_lane(self, p: QPainter, position: int, track: Track) -> None:
        m = self.model
        start, end = self._file_span()
        if end <= start:
            return
        rect = QRectF(start, self._lane_top(position), end - start, LANE_H)
        path = self._lane_path(rect)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.LANE)
        p.drawPath(path)

        if track.waveform is not None:
            t0 = m.time_at((start - self._content()[0]) / self._content()[1])
            t1 = m.time_at((end - self._content()[0]) / self._content()[1])
            peaks = track.waveform.peaks(t0, t1, max(1, int(rect.width() / BAR_STEP)))
            gain = 0.0 if track.muted else track.gain
            p.save()
            p.setClipPath(path)
            self._draw_bars(p, np.sqrt(np.minimum(peaks * gain, 1.0)), rect.adjusted(0, 3, 0, -3), theme.track_color(position), 2.2)
            p.restore()

        p.setPen(QPen(theme.LINE_STRONG, 2))
        if m.view_start <= 0:
            p.drawLine(QPointF(rect.left() + 1, rect.top() + 4), QPointF(rect.left() + 1, rect.bottom() - 4))
        if m.view_end >= m.duration:
            p.drawLine(QPointF(rect.right() - 1, rect.top() + 4), QPointF(rect.right() - 1, rect.bottom() - 4))

    def _paint_gutter(self, p: QPainter, position: int, track: Track) -> None:
        top = self._lane_top(position)
        p.setFont(theme.ui_font(13, QFont.Weight.Medium))
        p.setPen(theme.TEXT if not track.muted else theme.FAINT)
        p.drawText(QPointF(PAD_X, top + LANE_H / 2 - 6), track.name)
        value = f"{round(track.gain * 100)}%"
        p.setFont(theme.mono_font(12))
        p.setPen(theme.MUTED)
        p.drawText(QPointF(PAD_X + GUTTER - p.fontMetrics().horizontalAdvance(value), top + LANE_H / 2 - 6), value)

        icons.paint(p, "speaker-off" if track.muted else "speaker", self._mute(position).adjusted(3, 3, -3, -3), theme.MUTED)

        slider = self._slider(position)
        y = slider.center().y()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.LINE)
        p.drawRoundedRect(QRectF(slider.left(), y - 2, slider.width(), 4), 2, 2)
        filled = slider.width() * track.gain / MAX_GAIN
        p.setBrush(theme.FAINT if track.muted else theme.track_color(position))
        p.drawRoundedRect(QRectF(slider.left(), y - 2, filled, 4), 2, 2)
        p.setBrush(theme.TEXT)
        p.drawEllipse(QPointF(slider.left() + filled, y), 7, 7)

    def _paint_cuts(self, p: QPainter) -> None:
        m = self.model
        start, end = self._file_span()
        top, bottom = self._ruler_top() + RULER_H, self._lanes_bottom()
        if m.head_is_cut and self._x(m.cut_in) > start:
            self._hatch(p, QRectF(start, top, min(self._x(m.cut_in), end) - start, bottom - top))
        if m.tail_is_cut and self._x(m.cut_out) < end:
            left = max(self._x(m.cut_out), start)
            self._hatch(p, QRectF(left, top, end - left, bottom - top))

    def _paint_edges(self, p: QPainter) -> None:
        """Fade lanes that continue past the edge of the view."""
        m = self.model
        left, width = self._content()
        top, bottom = self._ruler_top() + RULER_H, self._lanes_bottom()
        fade = 36
        clear = QColor(theme.PANEL)
        clear.setAlpha(0)
        if m.view_start > 0:
            gradient = QLinearGradient(left, 0, left + fade, 0)
            gradient.setColorAt(0, theme.PANEL)
            gradient.setColorAt(1, clear)
            p.fillRect(QRectF(left, top, fade, bottom - top), QBrush(gradient))
        if m.view_end < m.duration:
            right = left + width
            gradient = QLinearGradient(right, 0, right - fade, 0)
            gradient.setColorAt(0, theme.PANEL)
            gradient.setColorAt(1, clear)
            p.fillRect(QRectF(right - fade, top, fade, bottom - top), QBrush(gradient))

    def _paint_handles(self, p: QPainter) -> None:
        m = self.model
        top, bottom = self._ruler_top(), self._lanes_bottom()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.ACCENT)
        if m.head_is_cut and m.view_start <= m.cut_in <= m.view_end:
            x = self._x(m.cut_in)
            p.drawRoundedRect(QRectF(x - 1.5, top, 3, bottom - top), 1.5, 1.5)
            p.drawRoundedRect(QRectF(x - 1.5, top + 2, 11, 18), 4, 4)
        if m.tail_is_cut and m.view_start <= m.cut_out <= m.view_end:
            x = self._x(m.cut_out)
            p.drawRoundedRect(QRectF(x - 1.5, top, 3, bottom - top), 1.5, 1.5)
            p.drawRoundedRect(QRectF(x - 9.5, top + 2, 11, 18), 4, 4)

    def _paint_playhead(self, p: QPainter) -> None:
        m = self.model
        rect = self._overview()
        p.setPen(QPen(theme.ACCENT, 2))
        x = self._ox(m.playhead)
        p.drawLine(QPointF(x, rect.top() + 2), QPointF(x, rect.bottom() - 2))

        if not m.view_start <= m.playhead <= m.view_end:
            return
        x = self._x(m.playhead)
        top = self._ruler_top()
        p.setPen(QPen(theme.TEXT, 2))
        p.drawLine(QPointF(x, top + 8), QPointF(x, self._lanes_bottom() + 2))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.TEXT)
        p.drawPolygon(QPolygonF([QPointF(x, top + 3), QPointF(x + 5, top + 8), QPointF(x, top + 13), QPointF(x - 5, top + 8)]))

    def _combined_peaks(self, start: float, end: float, count: int) -> np.ndarray | None:
        waves = [t.waveform.peaks(start, end, count) for t in self.tracks if t.waveform is not None]
        return np.max(waves, axis=0) if waves else None

    @staticmethod
    def _draw_bars(p: QPainter, peaks: np.ndarray, rect: QRectF, color: QColor, width: float) -> None:
        if len(peaks) == 0:
            return
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        step = rect.width() / len(peaks)
        middle = rect.center().y()
        reach = rect.height() / 2 - width / 2
        xs = rect.left() + (np.arange(len(peaks)) + 0.5) * step
        halves = np.maximum(0.4, peaks * reach)
        p.drawLines([QLineF(x, middle - h, x, middle + h) for x, h in zip(xs.tolist(), halves.tolist())])

    @staticmethod
    def _hatch(p: QPainter, rect: QRectF) -> None:
        if rect.width() <= 0:
            return
        p.fillRect(rect, QColor(14, 12, 19, 160))
        p.fillRect(rect, QBrush(QColor(14, 12, 19, 120), Qt.BrushStyle.BDiagPattern))

    # Input

    def _in_detail(self, pos: QPointF) -> bool:
        left, width = self._content()
        return left <= pos.x() <= left + width and self._ruler_top() <= pos.y() <= self._lanes_bottom()

    def _time_at_x(self, x: float) -> float:
        left, width = self._content()
        return self.model.clamp_time(self.model.time_at((x - left) / width))

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.model is None:
            return
        pos = event.position()
        over_overview = self._overview().adjusted(0, 0, 0, FUNNEL_H).contains(pos)
        if not (self._in_detail(pos) or over_overview):
            event.ignore()
            return
        delta = event.angleDelta()
        dx, dy = delta.x(), delta.y()
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier or abs(dx) > abs(dy):
            amount = dx if abs(dx) > abs(dy) else dy
            self.model.pan(-amount / 120 * WHEEL_PAN * self.model.span)
        elif dy:
            left, width = self._content()
            if over_overview:
                anchor = self.model.fraction_of(self.model.playhead)
                anchor = anchor if 0 <= anchor <= 1 else 0.5
            else:
                anchor = (pos.x() - left) / width
            self.model.zoom(anchor, 2 ** (-dy / 120 * WHEEL_ZOOM))
        event.accept()
        self.refresh()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.model is None or event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position()
        for position in range(len(self.tracks)):
            if self._mute(position).contains(pos):
                self.mute_toggled.emit(position)
                return
            if self._slider(position).adjusted(-8, -6, 8, 6).contains(pos):
                self._drag, self._drag_track = "gain", position
                self._set_gain_from(pos.x())
                return
        if self._overview().contains(pos):
            self._drag = "overview"
            self._center_overview(pos.x())
        elif self._in_detail(pos):
            self._drag = "scrub"
            self.scrub_started.emit()
            self.playhead_requested.emit(self._time_at_x(pos.x()))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.model is None:
            return
        pos = event.position()
        if self._drag == "scrub":
            self.playhead_requested.emit(self._time_at_x(pos.x()))
        elif self._drag == "overview":
            self._center_overview(pos.x())
        elif self._drag == "gain":
            self._set_gain_from(pos.x())
        else:
            pointing = self._overview().contains(pos) or any(
                self._mute(i).contains(pos) or self._slider(i).adjusted(-8, -6, 8, 6).contains(pos)
                for i in range(len(self.tracks))
            )
            self.setCursor(Qt.CursorShape.PointingHandCursor if pointing else Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag == "scrub":
            self.scrub_finished.emit()
        self._drag = None

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self.model is None:
            return
        pos = event.position()
        if self._overview().contains(pos):
            self.model.show_all()
            self.refresh()
            return
        for position in range(len(self.tracks)):
            if self._slider(position).adjusted(-8, -6, 8, 6).contains(pos):
                self.gain_changed.emit(position, 1.0)
                return
        self.mousePressEvent(event)

    def _center_overview(self, x: float) -> None:
        rect = self._overview()
        fraction = min(max((x - rect.left()) / rect.width(), 0.0), 1.0)
        self.model.center_on(fraction * self.model.duration)
        self.refresh()

    def _set_gain_from(self, x: float) -> None:
        slider = self._slider(self._drag_track)
        gain = min(max((x - slider.left()) / slider.width() * MAX_GAIN, 0.0), MAX_GAIN)
        if abs(gain - 1.0) < 0.04:
            gain = 1.0
        self.gain_changed.emit(self._drag_track, round(gain, 2))
