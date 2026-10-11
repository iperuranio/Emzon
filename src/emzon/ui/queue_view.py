"""The render queue: a ring in the header and the list it opens."""

from __future__ import annotations

import subprocess
import sys

from PySide6.QtCore import QPoint, QRectF, QSize, Qt
from PySide6.QtGui import QFont, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from emzon.export.queue import ExportQueue, Job, State
from emzon.media.tools import NO_WINDOW
from emzon.ui import icons, strings, theme
from emzon.ui.widgets import IconButton

ROW_HEIGHT = 44
POPOVER_WIDTH = 400


def reveal(path) -> None:
    if sys.platform == "win32":
        subprocess.Popen(["explorer", f"/select,{path}"], creationflags=NO_WINDOW)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path.parent)])


def _ring(painter: QPainter, rect: QRectF, fraction: float, color) -> None:
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(theme.LINE, 2.5))
    painter.drawEllipse(rect)
    if fraction > 0:
        pen = QPen(color, 2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 90 * 16, -round(360 * 16 * min(fraction, 1.0)))


class QueueButton(QPushButton):
    """Present only while the queue holds jobs: overall progress and how many there are."""

    def __init__(self, queue: ExportQueue, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.queue = queue
        self.setToolTip(strings.QUEUE_TIP)
        self.setAccessibleName(strings.QUEUE_TIP)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self.setStyleSheet(f"QPushButton {{ background: {theme.RAISED.name()}; border: none; border-radius: 10px; }}")
        queue.changed.connect(self._sync)
        self._sync()

    def _sync(self) -> None:
        count = len(self.queue.jobs)
        self.setVisible(count > 0)
        width = 46 + self.fontMetrics().horizontalAdvance(str(count))
        self.setFixedWidth(width)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        jobs = self.queue.jobs
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        active = [j for j in jobs if j.state.active]
        failed = any(j.state is State.FAILED for j in jobs)
        if active:
            fraction = sum(j.progress for j in active) / len(active)
            color = theme.ACCENT
        else:
            fraction = 1.0
            color = theme.ERROR if failed else theme.OK
        _ring(painter, QRectF(10, 9, 18, 18), fraction, color)
        painter.setPen(theme.TEXT)
        painter.setFont(theme.mono_font(13))
        painter.drawText(QRectF(34, 0, self.width() - 40, self.height()), Qt.AlignmentFlag.AlignVCenter, str(len(jobs)))


class JobRow(QWidget):
    def __init__(self, queue: ExportQueue, job: Job, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.queue = queue
        self.job = job
        self.setFixedHeight(ROW_HEIGHT)
        row = QHBoxLayout(self)
        row.setContentsMargins(40, 0, 6, 0)
        row.setSpacing(10)
        self.name = QLabel()
        self.status = QLabel()
        self.status.setFont(theme.mono_font(12))
        self.action = IconButton("close", strings.JOB_CANCEL, size=16)
        self.action.setFixedSize(28, 28)
        self.action.clicked.connect(self._act)
        row.addWidget(self.name, 1)
        row.addWidget(self.status)
        row.addWidget(self.action)
        self.sync()

    def sync(self) -> None:
        job = self.job
        self.name.setText(self.fontMetrics().elidedText(job.output.name, Qt.TextElideMode.ElideMiddle, 250))
        tips = []
        status, color = "", theme.ACCENT_SOFT
        if job.state is State.RUNNING:
            status = f"{int(job.progress * 100)}%"
        elif job.state is State.WAITING:
            status, color = strings.JOB_WAITING, theme.MUTED
        elif job.state is State.FINISHING:
            status = strings.JOB_FINISHING
        elif job.state is State.FAILED:
            status, color = strings.JOB_FAILED, theme.ERROR
            tips.append(job.error)
        elif job.state is State.CANCELLED:
            status, color = strings.JOB_CANCELLED, theme.MUTED
        if job.note:
            tips.append(job.note)
        if job.software:
            tips.append(strings.JOB_SOFTWARE)
        if job.kept_original:
            tips.append(strings.JOB_KEPT.format(error=job.error))
        self.status.setText(status)
        self.status.setStyleSheet(f"color: {color.name()};")
        self.name.setStyleSheet(f"color: {(theme.TEXT if job.state.active or job.state is State.DONE else theme.MUTED).name()};")
        self.setToolTip("\n".join(t for t in tips if t))

        if job.state is State.DONE:
            self.action.setIcon(icons.icon("folder", theme.MUTED, 16))
            self.action.setToolTip(strings.JOB_REVEAL)
            self.action.setAccessibleName(strings.JOB_REVEAL)
            self.action.show()
        elif job.state in (State.WAITING, State.RUNNING):
            self.action.setIcon(icons.icon("close", theme.MUTED, 16))
            self.action.setToolTip(strings.JOB_CANCEL)
            self.action.setAccessibleName(strings.JOB_CANCEL)
            self.action.show()
        else:
            self.action.hide()
        self.update()

    def _act(self) -> None:
        if self.job.state is State.DONE:
            reveal(self.job.output)
        else:
            self.queue.cancel(self.job)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        icon_rect = QRectF(10, (ROW_HEIGHT - 20) / 2, 20, 20)
        state = self.job.state
        if state in (State.RUNNING, State.FINISHING):
            _ring(painter, icon_rect.adjusted(1, 1, -1, -1), self.job.progress, theme.ACCENT)
        else:
            name, color = {
                State.WAITING: ("clock", theme.MUTED),
                State.DONE: ("check", theme.OK),
                State.FAILED: ("alert", theme.ERROR),
                State.CANCELLED: ("close", theme.FAINT),
            }[state]
            icons.paint(painter, name, icon_rect, color)


class QueuePopover(QFrame):
    def __init__(self, queue: ExportQueue, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.queue = queue
        self.setObjectName("popover")
        self.setStyleSheet(
            f"QFrame#popover {{ background: {theme.LANE.name()}; border: 1px solid {theme.LINE.name()}; border-radius: 14px; }}"
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedWidth(POPOVER_WIDTH)
        self._column = QVBoxLayout(self)
        self._column.setContentsMargins(6, 6, 6, 8)
        self._column.setSpacing(0)
        self._rows: dict[int, JobRow] = {}
        self._list = QVBoxLayout()
        self._list.setSpacing(0)
        self._column.addLayout(self._list)
        self.clear_button = QPushButton(strings.QUEUE_CLEAR)
        self.clear_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.setFont(theme.ui_font(13, QFont.Weight.Medium))
        self.clear_button.clicked.connect(queue.clear_finished)
        self._column.addSpacing(6)
        self._column.addWidget(self.clear_button, 0, Qt.AlignmentFlag.AlignRight)
        queue.changed.connect(self._sync)

    def open_below(self, anchor: QWidget) -> None:
        self._sync()
        corner = anchor.mapToGlobal(QPoint(anchor.width(), anchor.height() + 6))
        self.move(corner.x() - self.width(), corner.y())
        self.show()

    def _sync(self) -> None:
        jobs = list(reversed(self.queue.jobs))
        ids = {job.id for job in jobs}
        for job_id in list(self._rows):
            if job_id not in ids:
                self._rows.pop(job_id).deleteLater()
        for index, job in enumerate(jobs):
            row = self._rows.get(job.id)
            if row is None:
                row = self._rows[job.id] = JobRow(self.queue, job, self)
            self._list.insertWidget(index, row)
            row.sync()
        self.clear_button.setVisible(any(not job.state.active for job in jobs))
        if not jobs:
            self.hide()
        self.adjustSize()

    def sizeHint(self) -> QSize:
        return QSize(POPOVER_WIDTH, super().sizeHint().height())
