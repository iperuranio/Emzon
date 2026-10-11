"""The main window: one clip, its video, its timeline."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from emzon.media.probe import Clip, ProbeError, probe
from emzon.media.tools import ToolMissing
from emzon.media.waveform import load_waveform
from emzon.player.mpv_widget import MpvWidget
from emzon.tasks import Tasks
from emzon.timefmt import format_duration, format_time
from emzon.timeline.model import Timeline
from emzon.timeline.view import TimelineView, Track
from emzon.ui import strings, theme
from emzon.ui.widgets import ActionButton, IconButton, PlayButton

START_BEFORE_END = 30.0
END_TOLERANCE = 0.05


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(strings.APP_NAME)
        self.setAcceptDrops(True)
        self.resize(1440, 900)
        self.setMinimumSize(960, 640)

        self.clip: Clip | None = None
        self.model: Timeline | None = None
        self.tracks: list[Track] = []
        self._generation = 0
        self._resume_after_scrub = False
        self.tasks = Tasks(self)
        self.tasks.finished.connect(self._on_task)

        self.player = MpvWidget()
        self.player.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.player.time_changed.connect(self._on_time)
        self.player.pause_changed.connect(self._on_pause)

        self.timeline = TimelineView()
        self.timeline.playhead_requested.connect(self._seek)
        self.timeline.scrub_started.connect(self._scrub_started)
        self.timeline.scrub_finished.connect(self._scrub_finished)
        self.timeline.gain_changed.connect(self._set_gain)
        self.timeline.mute_toggled.connect(self._toggle_mute)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_header())
        layout.addWidget(self._build_stage(), 1)
        layout.addWidget(self._build_panel())
        self.setCentralWidget(central)
        self._bind_keys()
        self._show_empty()

    # Building

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(56)
        row = QHBoxLayout(header)
        row.setContentsMargins(20, 0, 16, 0)
        row.setSpacing(6)
        open_button = IconButton("folder", strings.OPEN_TIP)
        open_button.clicked.connect(self.choose_file)
        row.addWidget(open_button)
        self.file_label = QLabel()
        self.file_label.setFont(theme.ui_font(14, QFont.Weight.Medium))
        self.file_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        row.addSpacing(6)
        row.addWidget(self.file_label, 1)
        return header

    def _build_stage(self) -> QWidget:
        self.stage = QStackedWidget()

        empty = QWidget()
        column = QVBoxLayout(empty)
        column.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint = QLabel(strings.DROP_HINT)
        hint.setFont(theme.ui_font(20, QFont.Weight.Medium))
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        open_button = QPushButton(strings.OPEN)
        open_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        open_button.clicked.connect(self.choose_file)
        column.addWidget(hint)
        column.addSpacing(16)
        column.addWidget(open_button, 0, Qt.AlignmentFlag.AlignCenter)
        self.empty_page = empty

        video = QWidget()
        frame = QVBoxLayout(video)
        frame.setContentsMargins(24, 4, 24, 14)
        frame.addWidget(self.player)
        self.video_page = video

        message = QWidget()
        column = QVBoxLayout(message)
        column.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_title = QLabel()
        self.message_title.setFont(theme.ui_font(18, QFont.Weight.DemiBold))
        self.message_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_detail = QLabel()
        self.message_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_detail.setWordWrap(True)
        self.message_detail.setStyleSheet(f"color: {theme.MUTED.name()};")
        column.addWidget(self.message_title)
        column.addSpacing(8)
        column.addWidget(self.message_detail)
        self.message_page = message

        for page in (self.empty_page, self.video_page, self.message_page):
            self.stage.addWidget(page)
        return self.stage

    def _build_panel(self) -> QWidget:
        self.panel = QWidget()
        self.panel.setObjectName("panel")
        self.panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        column = QVBoxLayout(self.panel)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self.timeline)

        bar = QWidget()
        bar.setFixedHeight(64)
        row = QHBoxLayout(bar)
        row.setContentsMargins(24, 0, 24, 8)
        row.setSpacing(10)

        self.cut_head_button = ActionButton(strings.CUT_HEAD, "cut-head", "Q", strings.CUT_HEAD_TIP)
        self.cut_head_button.clicked.connect(self.cut_head)
        self.play_button = PlayButton(strings.PLAY_TIP)
        self.play_button.clicked.connect(self.toggle_play)
        self.cut_tail_button = ActionButton(strings.CUT_TAIL, "cut-tail", "W", strings.CUT_TAIL_TIP)
        self.cut_tail_button.clicked.connect(self.cut_tail)

        self.time_label = QLabel()
        self.time_label.setFont(theme.mono_font(20, QFont.Weight.Medium))
        self.time_label.setMinimumWidth(110)
        selection_name = QLabel(strings.SELECTION)
        selection_name.setStyleSheet(f"color: {theme.MUTED.name()};")
        self.selection_label = QLabel()
        self.selection_label.setFont(theme.mono_font(13))
        self.selection_label.setStyleSheet(f"color: {theme.ACCENT_SOFT.name()};")

        row.addWidget(self.cut_head_button)
        row.addWidget(self.play_button)
        row.addWidget(self.cut_tail_button)
        row.addSpacing(14)
        row.addWidget(self.time_label)
        row.addSpacing(6)
        row.addWidget(selection_name)
        row.addWidget(self.selection_label)
        row.addStretch(1)
        column.addWidget(bar)
        return self.panel

    def _bind_keys(self) -> None:
        bindings = {
            "Space": self.toggle_play,
            "Q": self.cut_head,
            "W": self.cut_tail,
            "F": self.fit_selection,
            "Left": lambda: self.step(-1.0),
            "Right": lambda: self.step(1.0),
            "Shift+Left": lambda: self.step_frames(-1),
            "Shift+Right": lambda: self.step_frames(1),
            "Ctrl+O": self.choose_file,
        }
        for number in range(1, 10):
            bindings[str(number)] = lambda position=number - 1: self._toggle_mute(position)
        for key, action in bindings.items():
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
            shortcut.activated.connect(action)

    # Opening

    def choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, strings.OPEN_DIALOG, "", strings.VIDEO_FILTER)
        if path:
            self.open_path(Path(path))

    def open_path(self, path: Path) -> None:
        self._generation += 1
        self.player.set_paused(True)
        self.file_label.setText(path.name)
        self._show_message(strings.LOADING, "")
        self.tasks.submit(("probe", self._generation), probe, path)

    def _on_task(self, key, result, error) -> None:
        kind, generation, *rest = key
        if generation != self._generation:
            return
        if kind == "probe":
            if error:
                self._show_open_error(error)
            else:
                self._load(result)
        elif kind == "waveform":
            track = self.tracks[rest[0]]
            track.waveform = result
            track.failed = error is not None
            self.timeline.refresh()

    def _load(self, clip: Clip) -> None:
        self.clip = clip
        self.model = Timeline(clip.duration, clip.fps)
        self.model.move_playhead(max(0.0, clip.duration - START_BEFORE_END))
        self.tracks = [Track(strings.track_name(t.position, t.title)) for t in clip.audio]
        self.timeline.set_content(self.model, self.tracks)
        self.player.open(clip.path, len(self.tracks), [t.gain for t in self.tracks], self.model.playhead)
        for track in clip.audio:
            self.tasks.submit(("waveform", self._generation, track.position), load_waveform, clip.path, track.position)
        self.stage.setCurrentWidget(self.video_page)
        self.panel.show()
        self._update_labels()

    def _show_empty(self) -> None:
        self.stage.setCurrentWidget(self.empty_page)
        self.panel.hide()

    def _show_message(self, title: str, detail: str, error: bool = False) -> None:
        color = theme.ERROR if error else theme.TEXT
        self.message_title.setStyleSheet(f"color: {color.name()};")
        self.message_title.setText(title)
        self.message_detail.setText(detail)
        self.stage.setCurrentWidget(self.message_page)
        self.panel.hide()

    def _show_open_error(self, error: BaseException) -> None:
        if isinstance(error, ToolMissing):
            reason = strings.TOOL_MISSING.format(tool=error.args[0])
        elif isinstance(error, ProbeError) and str(error) == "no video stream":
            reason = strings.NO_VIDEO
        elif isinstance(error, ProbeError) and str(error) == "unknown duration":
            reason = strings.UNKNOWN_DURATION
        else:
            reason = strings.UNREADABLE
        self._show_message(
            strings.OPEN_FAILED.format(name=self.file_label.text()),
            strings.OPEN_FAILED_DETAIL.format(reason=reason),
            error=True,
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        files = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        files = [f for f in files if f.is_file()]
        if files:
            self.open_path(files[0])
            event.acceptProposedAction()

    # Playback

    def toggle_play(self) -> None:
        if self.model is None:
            return
        if self.player.paused and self.model.playhead >= self.model.duration - END_TOLERANCE:
            self._seek(self.model.cut_in)
        self.player.set_paused(not self.player.paused)

    def _on_time(self, time: float) -> None:
        if self.model is None or self.timeline.scrubbing:
            return
        self.model.move_playhead(time)
        if not self.player.paused:
            before = (self.model.view_start, self.model.view_end)
            self.model.follow_playhead()
            if before != (self.model.view_start, self.model.view_end):
                self.timeline.refresh()
        self.timeline.update()
        self._update_labels()

    def _on_pause(self, paused: bool) -> None:
        self.play_button.show_playing(not paused)

    def _seek(self, time: float) -> None:
        if self.model is None:
            return
        self.model.move_playhead(time)
        self.player.seek(self.model.playhead)
        self.timeline.update()
        self._update_labels()

    def _scrub_started(self) -> None:
        self._resume_after_scrub = not self.player.paused
        if self._resume_after_scrub:
            self.player.set_paused(True)

    def _scrub_finished(self) -> None:
        if self._resume_after_scrub:
            self.player.set_paused(False)
        self._resume_after_scrub = False

    def step(self, seconds: float) -> None:
        if self.model is None:
            return
        self.model.step(seconds)
        self.player.seek(self.model.playhead)
        self.timeline.refresh()
        self._update_labels()

    def step_frames(self, frames: int) -> None:
        if self.model is None:
            return
        self.step(frames / self.model.fps)

    # Editing

    def cut_head(self) -> None:
        if self.model is None:
            return
        self.model.cut_head()
        self.timeline.refresh()
        self._update_labels()

    def cut_tail(self) -> None:
        if self.model is None:
            return
        self.model.cut_tail()
        self.timeline.refresh()
        self._update_labels()

    def fit_selection(self) -> None:
        if self.model is None:
            return
        self.model.fit_selection()
        self.timeline.refresh()

    def _set_gain(self, position: int, gain: float) -> None:
        track = self.tracks[position]
        track.gain = gain
        if not track.muted:
            self.player.set_gain(position, gain)
        self.timeline.refresh()

    def _toggle_mute(self, position: int) -> None:
        if position >= len(self.tracks):
            return
        track = self.tracks[position]
        track.muted = not track.muted
        self.player.set_gain(position, 0.0 if track.muted else track.gain)
        self.timeline.refresh()

    def _update_labels(self) -> None:
        if self.model is None:
            return
        self.time_label.setText(format_time(self.model.playhead))
        self.selection_label.setText(format_duration(self.model.selection))

    def closeEvent(self, event) -> None:
        self.tasks.shutdown()
        self.player.shutdown()
        super().closeEvent(event)
