import os
from pathlib import Path

import pytest

from emzon.media.clips import Playlist, clips_in


def make(folder, name, age):
    path = folder / name
    path.write_bytes(b"x" * 20_000)
    os.utime(path, (1_700_000_000 - age, 1_700_000_000 - age))
    return path


def test_folder_lists_videos_newest_first(tmp_path):
    old = make(tmp_path, "old.mp4", 300)
    new = make(tmp_path, "new.MKV", 10)
    make(tmp_path, "notes.txt", 0)
    make(tmp_path, "export_edited.partial.mp4", 0)
    assert clips_in(tmp_path) == [new, old]


def test_playlist_starts_on_the_opened_clip(tmp_path):
    make(tmp_path, "a.mp4", 10)
    b = make(tmp_path, "b.mp4", 20)
    make(tmp_path, "c.mp4", 30)
    playlist = Playlist.around(b)
    assert playlist.current == b and playlist.position == "2/3"


def test_steps_stop_at_both_ends(tmp_path):
    a = make(tmp_path, "a.mp4", 10)
    b = make(tmp_path, "b.mp4", 20)
    playlist = Playlist.around(a)
    assert playlist.step(-1) is None and playlist.current == a
    assert playlist.step(1) == b
    assert playlist.step(1) is None and playlist.current == b


def test_empty_folder_has_no_playlist(tmp_path):
    assert Playlist.of_folder(tmp_path) is None


def test_a_clip_outside_any_listing_still_opens(tmp_path):
    odd = tmp_path / "odd.ts"
    odd.write_bytes(b"x")
    playlist = Playlist.around(odd)
    assert playlist.current == odd


def test_an_empty_playlist_is_an_error():
    with pytest.raises(ValueError):
        Playlist([])


def test_files_too_small_for_a_video_are_left_out(tmp_path):
    good = make(tmp_path, "good.mp4", 10)
    (tmp_path / "unfinished-altf10.mp4").write_bytes(b"x" * 1_000)
    assert clips_in(tmp_path) == [good]


def test_dropping_the_current_clip_moves_on_in_the_same_direction():
    files = [Path(n) for n in ("a.mp4", "b.mp4", "c.mp4", "d.mp4")]
    forward = Playlist(list(files), 1)
    assert forward.drop(files[1], 1) == files[2] and forward.position == "2/3"
    backward = Playlist(list(files), 2)
    assert backward.drop(files[2], -1) == files[1] and backward.position == "2/3"
    last = Playlist(list(files), 3)
    assert last.drop(files[3], 1) == files[2]


def test_dropping_another_clip_keeps_the_current_one():
    files = [Path(n) for n in ("a.mp4", "b.mp4", "c.mp4")]
    playlist = Playlist(list(files), 2)
    assert playlist.drop(files[0]) == files[2] and playlist.position == "2/2"


def test_dropping_the_only_clip_leaves_nothing():
    playlist = Playlist([Path("a.mp4")])
    assert playlist.drop(Path("a.mp4")) is None and playlist.files == []
