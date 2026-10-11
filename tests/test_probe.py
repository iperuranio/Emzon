from pathlib import Path

import pytest

from emzon.media.probe import ProbeError, parse_probe

SHADOWPLAY = {
    "streams": [
        {"codec_type": "video", "codec_name": "h264", "width": 2560, "height": 1440,
         "avg_frame_rate": "60/1", "r_frame_rate": "60/1"},
        {"codec_type": "audio", "codec_name": "aac", "channels": 2},
        {"codec_type": "audio", "codec_name": "aac", "channels": 1, "tags": {"title": "Mic"}},
    ],
    "format": {"duration": "300.016667"},
}


def test_reads_video_and_every_audio_track():
    clip = parse_probe(SHADOWPLAY, Path("clip.mp4"))
    assert clip.duration == pytest.approx(300.016667)
    assert clip.fps == 60
    assert (clip.width, clip.height, clip.video_codec) == (2560, 1440, "h264")
    assert [(t.position, t.channels, t.title) for t in clip.audio] == [(0, 2, None), (1, 1, "Mic")]


def test_ntsc_frame_rates_stay_exact():
    data = {**SHADOWPLAY, "streams": [{**SHADOWPLAY["streams"][0], "avg_frame_rate": "60000/1001"}]}
    assert parse_probe(data, Path("clip.mp4")).fps == pytest.approx(59.94, abs=0.01)


def test_cover_art_is_not_the_video():
    data = {"streams": [{"codec_type": "video", "disposition": {"attached_pic": 1}}], "format": {"duration": "5"}}
    with pytest.raises(ProbeError):
        parse_probe(data, Path("song.mp3"))


def test_missing_duration_is_an_error():
    data = {"streams": SHADOWPLAY["streams"], "format": {}}
    with pytest.raises(ProbeError):
        parse_probe(data, Path("clip.mp4"))
