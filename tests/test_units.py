import pytest

from emzon.units import codec_name, format_fps, format_size


@pytest.mark.parametrize(("size", "expected"), [(400, "1 KB"), (52_000, "52 KB"), (312_400_000, "312 MB"), (1_240_000_000, "1,2 GB")])
def test_format_size(size, expected):
    assert format_size(size) == expected


@pytest.mark.parametrize(("fps", "expected"), [(60.0, "60 fps"), (59.94006, "59,94 fps"), (29.999, "30 fps")])
def test_format_fps(fps, expected):
    assert format_fps(fps) == expected


def test_codec_names():
    assert codec_name("h264") == "H.264"
    assert codec_name("hevc") == "HEVC"
    assert codec_name("vp8") == "VP8"
