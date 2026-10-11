"""The main window: one clip, its video, its timeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from emzon import settings
from emzon.export.jobs import Kind, Request, destination, video_extension
from emzon.export.queue import ExportQueue, Job
from emzon.media.clips import Playlist
from emzon.media.probe import Clip, ProbeError, probe
from emzon.media.thumbnails import Thumbnails
from emzon.media import proxy, tools
from emzon.media.tools import ToolMissing
from emzon.media.waveform import GROUP as WAVEFORM_GROUP
from emzon.media.waveform import load_waveform
from emzon.player.mpv_widget import MpvWidget
from emzon.tasks import Tasks
from emzon.timefmt import format_length, format_time
from emzon.timeline.model import Timeline
from emzon.timeline.view import TimelineView, Track
from emzon.ui import strings, theme
from emzon.ui.folder_panel import FolderPanel
from emzon.ui.queue_view import QueueButton, QueuePopover
from emzon.ui.settings_view import SettingsDialog
from emzon.ui.widgets import ActionButton, DropOverlay, ElidedLabel, IconButton, PlayButton, PreviewButton

log = logging.getLogger(__name__)

START_BEFORE_END = 30.0
END_TOLERANCE = 0.05
LOADING_DELAY_MS = 300
THUMBNAIL_REFRESH_MS = 80
SEEK_INTERVAL_MS = 16


@dataclass
class Snapshot:
    """What the user did to a clip, kept for the session."""

    duration: float
    playhead: float
    cut_in: float
    cut_out: float
    view_start: float
    view_end: float
    gains: list[float]
    muted: list[bool]


class MainWindow(QMainWindow):
    _proxy_progress = Signal(int, float)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(strings.APP_NAME)
        self.setAcceptDrops(True)
        self.setMinimumSize(1024, 700)
        if not self.restoreGeometry(settings.window_geometry()):
            self.resize(1440, 900)

        self.preferences = settings.load()
        self.clip: Clip | None = None
        self.model: Timeline | None = None
        self.tracks: list[Track] = []
        self.playlist: Playlist | None = None
        self.memory: dict[Path, Snapshot] = {}
        self._generation = 0
        self._loading_path: Path | None = None
        self._player_ready = False
        self._resume_after_scrub = False
        self._resume_after_load = False
        self._playing: Path | None = None

        self.tasks = Tasks(self)
        self.tasks.finished.connect(self._on_task)
        self.library_tasks = Tasks(self)
        self.library_tasks.finished.connect(self._on_library)
        self._library: dict[Path, tuple[Clip | None, int | None]] = {}
        self.proxy_tasks = Tasks(self, workers=1)
        self.proxy_tasks.finished.connect(self._on_proxy)
        self._proxy_progress.connect(self._on_proxy_progress)
        self.queue = ExportQueue(self)
        self.queue.replace_ready.connect(self._finish_replace)
        self.thumbnails = Thumbnails(self)
        self._thumbnail_timer = QTimer(self, singleShot=True, interval=THUMBNAIL_REFRESH_MS)
        self._thumbnail_timer.timeout.connect(lambda: self.timeline.refresh())
        self.thumbnails.ready.connect(self._thumbnail_timer.start)
        self._loading_timer = QTimer(self, singleShot=True, interval=LOADING_DELAY_MS)
        self._loading_timer.timeout.connect(self._show_loading)
        self._pending_seek: float | None = None
        self._seek_timer = QTimer(self, singleShot=True, interval=SEEK_INTERVAL_MS)
        self._seek_timer.timeout.connect(self._flush_seek)

        self.player = MpvWidget()
        self.player.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.player.time_changed.connect(self._on_time)
        self.player.pause_changed.connect(self._on_pause)
        self.player.loaded.connect(self._on_player_loaded)

        self.timeline = TimelineView()
        self.timeline.playhead_requested.connect(self._seek)
        self.timeline.scrub_started.connect(self._scrub_started)
        self.timeline.scrub_finished.connect(self._scrub_finished)
        self.timeline.gain_changed.connect(self._set_gain)
        self.timeline.mute_toggled.connect(self._toggle_mute)
        self.timeline.cuts_changed.connect(self._update_labels)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_header())
        middle = QHBoxLayout()
        middle.setContentsMargins(0, 0, 0, 0)
        middle.setSpacing(0)
        self.folder_panel = FolderPanel()
        self.folder_panel.open_requested.connect(self._open_from_panel)
        middle.addWidget(self.folder_panel)
        middle.addWidget(self._build_stage(), 1)
        layout.addLayout(middle, 1)
        layout.addWidget(self._build_panel())
        self.setCentralWidget(central)
        self.folder_panel.set_open(self.preferences.folder_panel, animated=False)
        self.drop_overlay = DropOverlay(self)
        self._bind_keys()
        self._show_empty()

    # Building

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(56)
        row = QHBoxLayout(header)
        row.setContentsMargins(20, 0, 16, 0)
        row.setSpacing(6)

        self.folder_button = IconButton("sidebar", strings.FOLDER_TIP)
        self.folder_button.clicked.connect(self.toggle_folder_panel)
        row.addWidget(self.folder_button)
        open_button = IconButton("folder", strings.OPEN_TIP)
        open_button.clicked.connect(self.choose_file)
        row.addWidget(open_button)

        self.navigation = QWidget()
        nav = QHBoxLayout(self.navigation)
        nav.setContentsMargins(6, 0, 0, 0)
        nav.setSpacing(2)
        divider = QWidget()
        divider.setFixedSize(1, 20)
        divider.setStyleSheet(f"background: {theme.LINE.name()};")
        self.previous_button = IconButton("chevron-left", strings.PREVIOUS_TIP, size=18)
        self.previous_button.clicked.connect(lambda: self.step_clip(-1))
        self.position_label = QLabel()
        self.position_label.setFont(theme.mono_font(13))
        self.position_label.setStyleSheet(f"color: {theme.MUTED.name()};")
        self.position_label.setMinimumWidth(44)
        self.position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next_button = IconButton("chevron-right", strings.NEXT_TIP, size=18)
        self.next_button.clicked.connect(lambda: self.step_clip(1))
        nav.addWidget(divider)
        nav.addSpacing(6)
        nav.addWidget(self.previous_button)
        nav.addWidget(self.position_label)
        nav.addWidget(self.next_button)
        row.addWidget(self.navigation)

        self.file_label = ElidedLabel()
        self.file_label.setFont(theme.ui_font(14, QFont.Weight.Medium))
        row.addSpacing(10)
        row.addWidget(self.file_label, 1)

        self.queue_button = QueueButton(self.queue)
        self.queue_popover = QueuePopover(self.queue, self)
        self.queue_button.clicked.connect(lambda: self.queue_popover.open_below(self.queue_button))
        row.addWidget(self.queue_button)
        settings_button = IconButton("sliders", strings.SETTINGS)
        settings_button.clicked.connect(self.open_settings)
        row.addWidget(settings_button)
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
        self.message_detail.setMaximumWidth(560)
        self.message_detail.setStyleSheet(f"color: {theme.MUTED.name()};")
        column.addWidget(self.message_title)
        column.addSpacing(8)
        column.addWidget(self.message_detail, 0, Qt.AlignmentFlag.AlignCenter)
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
        grid = QGridLayout(bar)
        grid.setContentsMargins(24, 0, 24, 8)
        grid.setHorizontalSpacing(10)

        self.time_label = QLabel()
        self.time_label.setFont(theme.mono_font(20, QFont.Weight.Medium))
        self.time_label.setMinimumWidth(110)
        self.length_label = QLabel()
        self.selection_label = QLabel()
        times = QHBoxLayout()
        times.setSpacing(6)
        times.addWidget(self.time_label)
        times.addSpacing(10)
        for name, value in ((strings.LENGTH, self.length_label), (strings.SELECTION, self.selection_label)):
            label = QLabel(name)
            label.setStyleSheet(f"color: {theme.MUTED.name()};")
            value.setFont(theme.mono_font(13))
            times.addWidget(label)
            times.addWidget(value)
            times.addSpacing(8)
        self.selection_label.setStyleSheet(f"color: {theme.ACCENT_SOFT.name()};")
        times.addStretch(1)

        self.cut_head_button = ActionButton(strings.CUT_HEAD, "cut-head", "Q", strings.CUT_HEAD_TIP)
        self.cut_head_button.clicked.connect(self.cut_head)
        self.play_button = PlayButton(strings.PLAY_TIP)
        self.play_button.clicked.connect(self.toggle_play)
        self.cut_tail_button = ActionButton(strings.CUT_TAIL, "cut-tail", "W", strings.CUT_TAIL_TIP)
        self.cut_tail_button.clicked.connect(self.cut_tail)
        controls = QHBoxLayout()
        controls.setSpacing(10)
        controls.addWidget(self.cut_head_button)
        controls.addWidget(self.play_button)
        controls.addWidget(self.cut_tail_button)

        self.preview_button = PreviewButton(self.preferences.preview_scale)
        self.preview_button.chosen.connect(self.set_preview_scale)
        self.save_audio_button = ActionButton(strings.SAVE_AUDIO, "wave", "A", strings.SAVE_AUDIO_TIP)
        self.save_audio_button.clicked.connect(lambda: self.save(Kind.AUDIO))
        self.save_video_button = ActionButton(strings.SAVE_VIDEO, "film", "Invio", strings.SAVE_VIDEO_TIP, primary=True)
        self.save_video_button.clicked.connect(lambda: self.save(Kind.VIDEO))
        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addStretch(1)
        actions.addWidget(self.preview_button)
        actions.addSpacing(6)
        actions.addWidget(self.save_audio_button)
        actions.addWidget(self.save_video_button)

        left, right, middle = QWidget(), QWidget(), QWidget()
        left.setLayout(times)
        right.setLayout(actions)
        middle.setLayout(controls)
        for layout in (times, actions, controls):
            layout.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(left, 0, 0)
        grid.addWidget(middle, 0, 1)
        grid.addWidget(right, 0, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(2, 1)
        self._transport = (grid, left, middle, right)
        column.addWidget(bar)
        return self.panel

    def _bind_keys(self) -> None:
        bindings = {
            "Space": self.toggle_play,
            "Q": self.cut_head,
            "W": self.cut_tail,
            "F": self.fit_selection,
            "A": lambda: self.save(Kind.AUDIO),
            "Return": lambda: self.save(Kind.VIDEO),
            "Enter": lambda: self.save(Kind.VIDEO),
            "Left": lambda: self.step(-1.0),
            "Right": lambda: self.step(1.0),
            "Shift+Left": lambda: self.step_frames(-1),
            "Shift+Right": lambda: self.step_frames(1),
            "PgUp": lambda: self.step_clip(-1),
            "PgDown": lambda: self.step_clip(1),
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
        start = str(self.clip.path.parent) if self.clip else ""
        path, _ = QFileDialog.getOpenFileName(self, strings.OPEN_DIALOG, start, strings.VIDEO_FILTER)
        if path:
            self.open_path(Path(path))

    def open_path(self, path: Path) -> None:
        if path.is_dir():
            playlist = Playlist.of_folder(path)
            if playlist is None:
                self._show_message(strings.NO_CLIPS.format(name=path.name), strings.NO_CLIPS_DETAIL, error=True)
                return
        else:
            playlist = Playlist.around(path)
        self.playlist = playlist
        self._open_clip(playlist.current)

    def step_clip(self, delta: int) -> None:
        if self.playlist is None:
            return
        target = self.playlist.step(delta)
        if target is not None:
            self._open_clip(target)

    def _open_clip(self, path: Path) -> None:
        self._remember()
        tools.stop_group(WAVEFORM_GROUP)
        tools.stop_group(proxy.GROUP)
        self._generation += 1
        self._player_ready = False
        self._playing = None
        self._loading_path = path
        self.player.set_paused(True)
        self.file_label.setText(path.name)
        self._update_navigation()
        self._loading_timer.start()
        self.tasks.submit(("probe", self._generation), probe, path)

    def _show_loading(self) -> None:
        if self._loading_path is not None:
            self._show_message(strings.LOADING, "")

    def _on_task(self, key, result, error) -> None:
        kind, generation, *rest = key
        if generation != self._generation:
            return
        if kind == "probe":
            self._loading_timer.stop()
            self._loading_path = None
            if error:
                log.warning("cannot open %s: %s", self.file_label.text(), error)
                self._show_open_error(error)
            else:
                self._load(result)
        elif kind == "waveform":
            track = self.tracks[rest[0]]
            track.waveform = result
            track.failed = error is not None
            if error:
                log.warning("waveform of track %d: %s", rest[0] + 1, error)
            self.timeline.refresh()

    def _load(self, clip: Clip) -> None:
        self.clip = clip
        self.model = Timeline(clip.duration, clip.fps)
        self.model.move_playhead(max(0.0, clip.duration - START_BEFORE_END))
        self.tracks = [Track(strings.track_name(t.position, t.title)) for t in clip.audio]
        self._restore(clip)
        self.timeline.set_content(self.model, self.tracks, clip.path, self.thumbnails)
        self._play_file(self._preview_source(clip))
        for track in clip.audio:
            self.tasks.submit(("waveform", self._generation, track.position), load_waveform, clip.path, track.position)
        self.stage.setCurrentWidget(self.video_page)
        self.panel.show()
        self.folder_panel.show_clip(clip)
        try:
            self._library[clip.path] = (clip, clip.path.stat().st_size)
            self.folder_panel.set_detail(clip.path, *self._library[clip.path])
        except OSError:
            pass
        self._update_labels()

    def _remember(self) -> None:
        if self.clip is None or self.model is None:
            return
        m = self.model
        self.memory[self.clip.path] = Snapshot(
            m.duration, m.playhead, m.cut_in, m.cut_out, m.view_start, m.view_end,
            [t.gain for t in self.tracks], [t.muted for t in self.tracks],
        )

    def _restore(self, clip: Clip) -> None:
        snapshot = self.memory.get(clip.path)
        if snapshot is None or abs(snapshot.duration - clip.duration) > 0.01 or len(snapshot.gains) != len(self.tracks):
            return
        m = self.model
        m.move_playhead(snapshot.playhead)
        m.cut_in, m.cut_out = snapshot.cut_in, snapshot.cut_out
        m.set_view(snapshot.view_start, snapshot.view_end - snapshot.view_start)
        for track, gain, muted in zip(self.tracks, snapshot.gains, snapshot.muted):
            track.gain, track.muted = gain, muted

    def _update_navigation(self) -> None:
        playlist = self.playlist
        show = playlist is not None and len(playlist.files) > 1
        self.navigation.setVisible(show)
        if show:
            self.position_label.setText(playlist.position)
            self.previous_button.setEnabled(playlist.index > 0)
            self.next_button.setEnabled(playlist.index < len(playlist.files) - 1)
        self._update_folder_panel()

    # Folder panel

    def toggle_folder_panel(self) -> None:
        self.preferences.folder_panel = not self.folder_panel.is_open
        settings.save(self.preferences)
        self.folder_panel.set_open(self.preferences.folder_panel)
        self._update_folder_panel()

    def _update_folder_panel(self) -> None:
        if self.playlist is None:
            return
        self.folder_panel.set_clips(self.playlist.files, self.playlist.current)
        for path in self.playlist.files:
            known = self._library.get(path)
            if known is not None:
                self.folder_panel.set_detail(path, *known)
            elif self.folder_panel.is_open:
                self._library[path] = (None, None)
                self.library_tasks.submit(("library", path), _describe, path)

    def _on_library(self, key, result, error) -> None:
        _kind, path = key
        if error:
            log.info("cannot describe %s: %s", path.name, error)
            result = (None, None)
        self._library[path] = result
        self.folder_panel.set_detail(path, *result)

    def _open_from_panel(self, path: Path) -> None:
        if self.playlist is None or path not in self.playlist.files or path == self.playlist.current:
            return
        self.playlist.index = self.playlist.files.index(path)
        self._open_clip(path)

    def _show_empty(self) -> None:
        self.stage.setCurrentWidget(self.empty_page)
        self.panel.hide()
        self._update_navigation()

    def _show_message(self, title: str, detail: str, error: bool = False) -> None:
        color = theme.ERROR if error else theme.TEXT
        self.message_title.setStyleSheet(f"color: {color.name()};")
        self.message_title.setText(title)
        self.message_detail.setText(detail)
        self.message_detail.setVisible(bool(detail))
        self.stage.setCurrentWidget(self.message_page)
        self.panel.hide()

    def _show_open_error(self, error: BaseException) -> None:
        self.clip = None
        self.model = None
        self.player.unload()
        self._playing = None
        if isinstance(error, ToolMissing):
            detail = strings.TOOL_MISSING.format(tool=error.args[0])
        elif isinstance(error, ProbeError) and str(error) == "no video stream":
            detail = strings.NO_VIDEO
        elif isinstance(error, ProbeError) and str(error) == "unknown duration":
            detail = strings.UNKNOWN_DURATION
        else:
            detail = strings.UNREADABLE
        self._show_message(strings.OPEN_FAILED.format(name=self.file_label.text()), detail, error=True)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._center_controls()

    def _center_controls(self) -> None:
        """Equal sides keep cut and play in the exact middle, as long as the window is wide enough."""
        grid, left, middle, right = self._transport
        side = max(left.sizeHint().width(), right.sizeHint().width())
        margins = grid.contentsMargins()
        room = self.width() - margins.left() - margins.right() - 2 * grid.horizontalSpacing()
        fits = room >= 2 * side + middle.sizeHint().width()
        for column in (0, 2):
            grid.setColumnMinimumWidth(column, side if fits else 0)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()
            self.drop_overlay.setGeometry(self.rect())
            self.drop_overlay.raise_()
            self.drop_overlay.show()

    def dragLeaveEvent(self, event) -> None:
        self.drop_overlay.hide()

    def dropEvent(self, event: QDropEvent) -> None:
        self.drop_overlay.hide()
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        paths = [p for p in paths if p.exists()]
        if paths:
            event.acceptProposedAction()
            self.open_path(paths[0])

    # Playback

    def toggle_play(self) -> None:
        if self.model is None or not self._player_ready:
            return
        if self.player.paused and self.model.playhead >= self.model.duration - END_TOLERANCE:
            self._seek(self.model.cut_in)
        self.player.set_paused(not self.player.paused)

    def _on_player_loaded(self) -> None:
        self._player_ready = True
        self._pending_seek = None
        if self.model is not None:
            self.player.seek(self.model.playhead)
        if self._resume_after_load:
            self._resume_after_load = False
            self.player.set_paused(False)

    # Preview resolution

    def _play_file(self, path: Path) -> None:
        """Load the clip or its preview copy, keeping position and play state."""
        if self.model is None or path == self._playing:
            return
        self._resume_after_load = self._playing is not None and not self.player.paused
        self._playing = path
        self._player_ready = False
        gains = [0.0 if t.muted else t.gain for t in self.tracks]
        self.player.open(path, len(self.tracks), gains, self.model.playhead)

    def _preview_source(self, clip: Clip) -> Path:
        """The preview copy if it is ready; otherwise the clip, while the copy is made."""
        scale = self.preferences.preview_scale
        self.preview_button.set_progress(None)
        if scale == 1:
            return clip.path
        try:
            ready = proxy.existing(clip.path, scale)
        except OSError as error:
            log.warning("preview copy of %s: %s", clip.path.name, error)
            ready = None
        if ready is not None:
            return ready
        tools.stop_group(proxy.GROUP)
        self.preview_button.set_progress(0.0)
        generation = self._generation
        self.proxy_tasks.submit(
            ("proxy", generation, scale), proxy.build, clip.path, scale, clip.duration,
            lambda fraction: self._proxy_progress.emit(generation, fraction),
        )
        return clip.path

    def _on_proxy_progress(self, generation: int, fraction: float) -> None:
        if generation == self._generation and self.preview_button.progress is not None:
            self.preview_button.set_progress(fraction)

    def _on_proxy(self, key, result, error) -> None:
        _kind, generation, scale = key
        if generation != self._generation or scale != self.preferences.preview_scale or self.clip is None:
            return
        if error:
            log.warning("preview copy of %s failed: %s", self.clip.path.name, error)
            self.preview_button.set_failed(str(error).splitlines()[-1] if str(error) else type(error).__name__)
            return
        self.preview_button.set_progress(None)
        self._play_file(result)

    def set_preview_scale(self, scale: int) -> None:
        self.preferences.preview_scale = scale
        settings.save(self.preferences)
        self.preview_button.set_scale(scale)
        if self.clip is not None:
            self._play_file(self._preview_source(self.clip))

    def _on_time(self, time: float) -> None:
        if self.model is None or not self._player_ready or self.timeline.scrubbing:
            return
        m = self.model
        # Follow a playhead the user can see; one they scrolled away from stays where it is.
        was_visible = m.view_start <= m.playhead <= m.view_end
        m.move_playhead(time)
        if was_visible:
            before = (m.view_start, m.view_end)
            m.follow_playhead()
            if before != (m.view_start, m.view_end):
                self.timeline.refresh()
        self.timeline.update()
        self._update_labels()

    def _on_pause(self, paused: bool) -> None:
        self.play_button.show_playing(not paused)
        self.play_button.setAccessibleName(strings.PLAY if paused else strings.PAUSE)

    def _seek(self, time: float) -> None:
        """Move the playhead now; the player follows at most once per frame."""
        if self.model is None:
            return
        self.model.move_playhead(time)
        self._pending_seek = self.model.playhead
        if not self._seek_timer.isActive():
            self._flush_seek()
            self._seek_timer.start()
        self.timeline.update()
        self._update_labels()

    def _flush_seek(self) -> None:
        if self._pending_seek is not None and self._player_ready:
            self.player.seek(self._pending_seek)
            self._pending_seek = None

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
        self._pending_seek = None
        if self._player_ready:
            self.player.seek(self.model.playhead)
        self.timeline.refresh()
        self._update_labels()

    def step_frames(self, frames: int) -> None:
        if self.model is None or not self._player_ready:
            return
        if not self.player.paused:
            self.player.set_paused(True)
        self._flush_seek()
        self.player.frame_step(frames > 0)

    # Editing

    def _sync_playhead(self) -> None:
        """During playback, take the player's own time rather than the last repaint's."""
        if self._player_ready and not self.player.paused and (time := self.player.time) is not None:
            self.model.move_playhead(time)

    def cut_head(self) -> None:
        if self.model is None:
            return
        self._sync_playhead()
        self.model.cut_head()
        self.timeline.refresh()
        self._update_labels()

    def cut_tail(self) -> None:
        if self.model is None:
            return
        self._sync_playhead()
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
        if self.model is None or position >= len(self.tracks):
            return
        track = self.tracks[position]
        track.muted = not track.muted
        self.player.set_gain(position, 0.0 if track.muted else track.gain)
        self.timeline.refresh()

    def _can_save(self, kind: Kind) -> bool:
        if self.model is None or self.clip is None:
            return False
        if self.model.selection < 1 / self.model.fps:
            return False
        return kind is Kind.VIDEO or bool(self.tracks)

    def _update_labels(self) -> None:
        if self.model is None:
            return
        self.time_label.setText(format_time(self.model.playhead))
        self.length_label.setText(format_length(self.model.duration))
        self.selection_label.setText(format_length(self.model.selection))
        self.save_video_button.setEnabled(self._can_save(Kind.VIDEO))
        self.save_audio_button.setEnabled(self._can_save(Kind.AUDIO))

    # Saving

    def save(self, kind: Kind) -> None:
        if not self._can_save(kind):
            return
        clip, m, prefs = self.clip, self.model, self.preferences
        gains = tuple(0.0 if t.muted else t.gain for t in self.tracks)
        note = ""
        replace = kind is Kind.VIDEO and prefs.replace_original
        target = clip.path.with_suffix(video_extension(clip.path))
        if replace and self.queue.replacing(clip.path):
            replace, note = False, strings.JOB_REPLACE_BUSY
        if replace and target != clip.path and target.exists():
            replace = False
        if not replace:
            target = destination(clip.path, kind, prefs.audio_format, prefs.export_folder, self.queue.reserved())
        # The frame under the playhead when the tail was cut belongs to the clip.
        end = min(m.duration, m.cut_out + 1 / m.fps) if m.tail_is_cut else m.duration
        request = Request(
            source=clip.path,
            kind=kind,
            start=m.cut_in,
            end=end,
            gains=gains,
            video_codec=clip.video_codec,
            destination=target,
            audio_format=prefs.audio_format,
            replace_original=replace,
        )
        job = self.queue.add(request)
        job.note = note

    def _finish_replace(self, job: Job) -> None:
        source = job.request.source
        current = self.clip is not None and self.clip.path == source
        if current:
            self.player.unload()
            self._playing = None
        self.queue.finish_replace(job)
        reopen = source
        self._library.pop(source, None)
        if not job.kept_original:
            self.thumbnails.forget(source)
            self.memory.pop(source, None)
            reopen = job.output
            if self.playlist is not None and source in self.playlist.files:
                self.playlist.files[self.playlist.files.index(source)] = job.output
        if current:
            self.clip = None
            self.model = None
            self._open_clip(reopen)

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.preferences, self)
        dialog.changed.connect(self._settings_changed)
        dialog.exec()

    def _settings_changed(self, preferences: settings.Preferences) -> None:
        if preferences.preview_scale != self.preview_button.scale:
            self.set_preview_scale(preferences.preview_scale)

    def can_quit(self) -> bool:
        """Whether another copy may close this one: never while exports would be lost."""
        return not self.queue.busy

    def quit_cleanly(self) -> None:
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QDialog) and widget.isVisible():
                widget.reject()
        self.queue_popover.hide()
        if self.close():
            QApplication.quit()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.queue.busy:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle(strings.QUIT_TITLE)
            box.setText(strings.QUIT_TEXT)
            quit_button = box.addButton(strings.QUIT_CONFIRM, QMessageBox.ButtonRole.DestructiveRole)
            keep = box.addButton(strings.QUIT_KEEP, QMessageBox.ButtonRole.RejectRole)
            box.setDefaultButton(keep)
            box.setEscapeButton(keep)
            box.exec()
            if box.clickedButton() is not quit_button:
                event.ignore()
                return
        settings.save_window_geometry(self.saveGeometry())
        self.queue.shutdown()
        self.thumbnails.shutdown()
        self.tasks.shutdown()
        self.library_tasks.shutdown()
        self.proxy_tasks.shutdown()
        tools.stop_all()
        self.player.shutdown()
        super().closeEvent(event)


def _describe(path: Path) -> tuple[Clip | None, int | None]:
    """What the folder panel shows for a clip: its probe and its size."""
    size = path.stat().st_size
    try:
        return probe(path), size
    except ProbeError:
        return None, size
