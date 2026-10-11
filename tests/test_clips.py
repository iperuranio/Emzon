import os

import pytest

from emzon.media.clips import Playlist, clips_in


def make(folder, name, age):
    path = folder / name
    path.write_bytes(b"x")
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
