"""What part of the clip is visible, where the playhead is and what will be kept."""

from __future__ import annotations

MIN_SPAN = 0.5
# Share of the visible span that may extend past either end of the file,
# so a real start or end never sits exactly on the edge of the view.
END_MARGIN = 0.02
FOLLOW_OFFSET = 0.1


class Timeline:
    def __init__(self, duration: float, fps: float = 60.0) -> None:
        if duration <= 0:
            raise ValueError("duration must be positive")
        if fps <= 0:
            raise ValueError("fps must be positive")
        self.duration = duration
        self.fps = fps
        self.playhead = 0.0
        self.cut_in = 0.0
        self.cut_out = duration
        self.view_start = 0.0
        self.view_end = 0.0
        self.show_all()

    @property
    def span(self) -> float:
        return self.view_end - self.view_start

    @property
    def max_span(self) -> float:
        return self.duration / (1 - 2 * END_MARGIN)

    @property
    def visible_file_span(self) -> float:
        return max(0.0, min(self.view_end, self.duration) - max(self.view_start, 0.0))

    @property
    def selection(self) -> float:
        return self.cut_out - self.cut_in

    @property
    def head_is_cut(self) -> bool:
        return self.cut_in > 0

    @property
    def tail_is_cut(self) -> bool:
        return self.cut_out < self.duration

    def time_at(self, fraction: float) -> float:
        return self.view_start + fraction * self.span

    def fraction_of(self, time: float) -> float:
        return (time - self.view_start) / self.span

    def clamp_time(self, time: float) -> float:
        return min(max(time, 0.0), self.duration)

    def set_view(self, start: float, span: float) -> None:
        span = min(max(span, MIN_SPAN), self.max_span)
        margin = span * END_MARGIN
        lowest = -margin
        highest = self.duration + margin - span
        start = min(max(start, lowest), max(lowest, highest))
        self.view_start = start
        self.view_end = start + span

    def show_all(self) -> None:
        span = self.max_span
        self.set_view(-END_MARGIN * span, span)

    def zoom(self, anchor_fraction: float, factor: float) -> None:
        """Scale the view while the time under the anchor stays put."""
        anchor = self.time_at(anchor_fraction)
        span = min(max(self.span * factor, MIN_SPAN), self.max_span)
        self.set_view(anchor - anchor_fraction * span, span)

    def pan(self, seconds: float) -> None:
        self.set_view(self.view_start + seconds, self.span)

    def center_on(self, time: float) -> None:
        self.set_view(time - self.span / 2, self.span)

    def move_playhead(self, time: float) -> None:
        self.playhead = self.clamp_time(time)

    def step(self, seconds: float) -> None:
        self.move_playhead(self.playhead + seconds)
        if not self.view_start <= self.playhead <= self.view_end:
            self.center_on(self.playhead)

    def step_frames(self, frames: int) -> None:
        self.step(frames / self.fps)

    def follow_playhead(self) -> None:
        """Keep a playing playhead in view by paging forward."""
        if self.playhead > self.view_end or self.playhead < self.view_start:
            self.set_view(self.playhead - self.span * FOLLOW_OFFSET, self.span)

    def cut_head(self) -> None:
        self.cut_in = self.playhead
        if self.cut_in >= self.cut_out:
            self.cut_out = self.duration

    def cut_tail(self) -> None:
        self.cut_out = self.playhead
        if self.cut_out <= self.cut_in:
            self.cut_in = 0.0

    def fit_selection(self) -> None:
        """Frame the kept part; if it is already framed, show the whole file."""
        padding = self.selection * 0.06
        target_span = min(max(self.selection + 2 * padding, MIN_SPAN), self.max_span)
        before = (self.view_start, self.view_end)
        self.set_view(self.cut_in - padding, target_span)
        unchanged = abs(before[0] - self.view_start) < 1e-3 and abs(before[1] - self.view_end) < 1e-3
        if unchanged:
            self.show_all()
