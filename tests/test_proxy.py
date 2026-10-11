import json
import os
import shutil
import subprocess

import pytest

from emzon.media import proxy

FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")
pytestmark = pytest.mark.skipif(not (FFMPEG and FFPROBE), reason="needs ffmpeg and ffprobe")


@pytest.fixture
def clip(tmp_path):
    path = tmp_path / "clip.mp4"
    subprocess.run(
        [FFMPEG, "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30:duration=4",
         "-f", "lavfi", "-i", "sine=duration=4", "-f", "lavfi", "-i", "sine=frequency=880:duration=4",
         "-map", "0:v", "-map", "1:a", "-map", "2:a", "-c:v", "libx264", "-g", "120", "-c:a", "aac", str(path)],
        check=True,
    )
    return path


def streams(path):
    return json.loads(subprocess.run(
        [FFPROBE, "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        check=True, capture_output=True,
    ).stdout)


def test_preview_copy_is_smaller_keyframe_only_and_keeps_every_track(clip, tmp_path):
    seen = []
    path = proxy.build(clip, 4, 4.0, seen.append, folder=tmp_path / "cache")
    info = streams(path)
    video = [s for s in info["streams"] if s["codec_type"] == "video"][0]
    assert (video["width"], video["height"]) == (160, 90)
    assert len([s for s in info["streams"] if s["codec_type"] == "audio"]) == 2
    assert float(info["format"]["duration"]) == pytest.approx(4.0, abs=0.1)
    keyframes = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=key_frame", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout.split()
    assert keyframes and {k.strip(",") for k in keyframes} == {"1"}
    assert seen and seen[-1] == pytest.approx(1.0, abs=0.05)


def test_a_finished_copy_is_found_again(clip, tmp_path):
    folder = tmp_path / "cache"
    assert proxy.existing(clip, 2, folder) is None
    built = proxy.build(clip, 2, 4.0, lambda _: None, folder=folder)
    assert proxy.existing(clip, 2, folder) == built
    assert proxy.existing(clip, 4, folder) is None


def test_a_changed_clip_needs_a_new_copy(clip, tmp_path):
    before = proxy.proxy_path(clip, 2, tmp_path)
    os.utime(clip, (1_700_000_000, 1_700_000_000))
    assert proxy.proxy_path(clip, 2, tmp_path) != before


def test_the_cache_drops_the_least_recently_used_copies(tmp_path):
    files = []
    for age, name in enumerate(["c.mkv", "b.mkv", "a.mkv"]):
        path = tmp_path / name
        path.write_bytes(b"x" * 100)
        os.utime(path, (1_700_000_000 - age * 10, 1_700_000_000 - age * 10))
        files.append(path)
    keep = tmp_path / "new.mkv"
    keep.write_bytes(b"x" * 100)
    proxy.prune(tmp_path, keep, limit=250)
    assert keep.exists() and files[0].exists()
    assert not files[2].exists() and not files[1].exists()


def test_a_broken_clip_fails_with_a_reason(tmp_path):
    broken = tmp_path / "broken.mp4"
    broken.write_bytes(b"nope")
    with pytest.raises(proxy.ProxyError):
        proxy.build(broken, 2, 1.0, lambda _: None, folder=tmp_path / "cache")
    assert not list((tmp_path / "cache").glob("*.partial*"))
