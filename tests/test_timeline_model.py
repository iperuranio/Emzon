import pytest

from emzon.timeline.model import END_MARGIN, MIN_SPAN, Timeline


def test_full_view_leaves_a_margin_past_both_ends():
    t = Timeline(300)
    margin = END_MARGIN * t.span
    assert t.view_start == pytest.approx(-margin)
    assert t.view_end == pytest.approx(300 + margin)
    assert t.visible_file_span == pytest.approx(300)


def test_zoom_keeps_the_time_under_the_cursor_in_place():
    t = Timeline(300)
    anchor = 0.7
    before = t.time_at(anchor)
    t.zoom(anchor, 0.25)
    assert t.time_at(anchor) == pytest.approx(before)
    assert t.span == pytest.approx(t.max_span * 0.25)


def test_zoom_stops_at_the_minimum_span():
    t = Timeline(300)
    for _ in range(100):
        t.zoom(0.5, 0.5)
    assert t.span == pytest.approx(MIN_SPAN)


def test_zoom_out_never_exceeds_the_whole_file():
    t = Timeline(300)
    t.zoom(0.5, 0.1)
    t.zoom(0.5, 100)
    assert t.span == pytest.approx(t.max_span)


def test_view_cannot_drift_past_the_end_margin():
    t = Timeline(300)
    t.zoom(0.5, 0.1)
    t.pan(10_000)
    assert t.view_end == pytest.approx(300 + END_MARGIN * t.span)
    t.pan(-10_000)
    assert t.view_start == pytest.approx(-END_MARGIN * t.span)


def test_cut_head_and_tail_at_the_playhead():
    t = Timeline(300)
    t.move_playhead(252)
    t.cut_head()
    t.move_playhead(262)
    t.cut_tail()
    assert (t.cut_in, t.cut_out) == (252, 262)
    assert t.selection == pytest.approx(10)


def test_cutting_the_head_past_the_tail_releases_the_tail():
    t = Timeline(300)
    t.move_playhead(100)
    t.cut_tail()
    t.move_playhead(150)
    t.cut_head()
    assert (t.cut_in, t.cut_out) == (150, 300)


def test_cutting_the_tail_before_the_head_releases_the_head():
    t = Timeline(300)
    t.move_playhead(200)
    t.cut_head()
    t.move_playhead(50)
    t.cut_tail()
    assert (t.cut_in, t.cut_out) == (0, 50)


def test_playhead_stays_inside_the_file():
    t = Timeline(300)
    t.move_playhead(-5)
    assert t.playhead == 0
    t.move_playhead(500)
    assert t.playhead == 300


def test_frame_step_uses_the_frame_rate():
    t = Timeline(300, fps=60)
    t.move_playhead(10)
    t.step_frames(1)
    assert t.playhead == pytest.approx(10 + 1 / 60)


def test_stepping_out_of_view_recentres_it():
    t = Timeline(300)
    t.zoom(0.5, 0.01)
    t.move_playhead(t.view_end)
    t.step(5)
    assert t.view_start <= t.playhead <= t.view_end


def test_fit_selection_toggles_with_the_whole_file():
    t = Timeline(300)
    t.move_playhead(252)
    t.cut_head()
    t.move_playhead(262)
    t.cut_tail()
    t.fit_selection()
    assert t.view_start < 252 and t.view_end > 262
    assert t.span < 15
    t.fit_selection()
    assert t.span == pytest.approx(t.max_span)


def test_follow_pages_forward_when_the_playhead_leaves_the_view():
    t = Timeline(300)
    t.zoom(0.0, 0.05)
    t.move_playhead(t.view_end + 1)
    t.follow_playhead()
    assert t.view_start < t.playhead < t.view_end


@pytest.mark.parametrize("duration", [0, -1])
def test_rejects_empty_clips(duration):
    with pytest.raises(ValueError):
        Timeline(duration)
