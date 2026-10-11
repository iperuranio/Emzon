"""Video output: libmpv's render API drawing into a QOpenGLWidget."""

from __future__ import annotations

import locale
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QOpenGLContext
from PySide6.QtOpenGLWidgets import QOpenGLWidget

import mpv
from emzon.player.audio_graph import MIX_LABEL, complex_graph, mix_filter, volume_filter
from emzon.ui import theme


class MpvWidget(QOpenGLWidget):
    time_changed = Signal(float)
    pause_changed = Signal(bool)
    loaded = Signal()
    _frame_ready = Signal()
    _time = Signal(object)
    _pause = Signal(object)
    _event_loaded = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # libmpv refuses to start under a locale with a decimal comma.
        locale.setlocale(locale.LC_NUMERIC, "C")
        self.player = mpv.MPV(
            vo="libmpv",
            hwdec="auto-safe",
            keep_open="always",
            idle="yes",
            pause=True,
            hr_seek="yes",
            osc="no",
            input_default_bindings="no",
            input_vo_keyboard="no",
            background_color=theme.BG.name(),
            audio_buffer=0.1,
        )
        self._render: mpv.MpvRenderContext | None = None
        self._gains: list[float] = []
        self._get_proc_address = mpv.MpvGlGetProcAddressFn(self._proc_address)

        self._frame_ready.connect(self.update, Qt.ConnectionType.QueuedConnection)
        self._time.connect(self._on_time)
        self._pause.connect(self._on_pause)
        self._event_loaded.connect(self.loaded)
        self.player.observe_property("time-pos", lambda _name, value: self._time.emit(value))
        self.player.observe_property("pause", lambda _name, value: self._pause.emit(value))
        self.player.register_event_callback(self._on_event)

    @property
    def paused(self) -> bool:
        return bool(self.player.pause)

    def open(self, path: Path, track_count: int, gains: Sequence[float], start: float) -> None:
        self.player.pause = True
        self._gains = list(gains)
        self.player["lavfi-complex"] = complex_graph(track_count)
        self.player.af = mix_filter(self._gains)
        self.player.loadfile(str(path), start=f"{start:.6f}")

    def set_gain(self, position: int, gain: float) -> None:
        self._gains[position] = gain
        try:
            self.player.command("af-command", MIX_LABEL, "volume", f"{gain:.3f}", volume_filter(position))
        except SystemError:
            # The filter chain is only built once audio flows; until then the
            # gains travel with the chain's definition.
            self.player.af = mix_filter(self._gains)

    def seek(self, time: float) -> None:
        self.player.command("seek", f"{time:.6f}", "absolute+exact")

    def set_paused(self, paused: bool) -> None:
        self.player.pause = paused

    def shutdown(self) -> None:
        self.makeCurrent()
        if self._render is not None:
            self._render.free()
            self._render = None
        self.doneCurrent()
        self.player.terminate()

    def initializeGL(self) -> None:
        self._render = mpv.MpvRenderContext(
            self.player, "opengl", opengl_init_params={"get_proc_address": self._get_proc_address}
        )
        self._render.update_cb = self._frame_ready.emit

    def paintGL(self) -> None:
        if self._render is None:
            return
        ratio = self.devicePixelRatioF()
        self._render.render(
            flip_y=True,
            opengl_fbo={
                "w": round(self.width() * ratio),
                "h": round(self.height() * ratio),
                "fbo": self.defaultFramebufferObject(),
            },
        )

    def _on_event(self, event) -> None:
        if event.event_id.value == mpv.MpvEventID.FILE_LOADED:
            self._event_loaded.emit()

    def _on_time(self, value) -> None:
        if value is not None:
            self.time_changed.emit(float(value))

    def _on_pause(self, value) -> None:
        if value is not None:
            self.pause_changed.emit(bool(value))

    @staticmethod
    def _proc_address(_ctx, name: bytes) -> int:
        context = QOpenGLContext.currentContext()
        return int(context.getProcAddress(name)) if context else 0
