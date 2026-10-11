import pytest

from emzon.timefmt import format_span, format_time


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0, "0:00,00"), (256.4, "4:16,40"), (59.999, "1:00,00"), (3600.5, "60:00,50")],
)
def test_format_time(seconds, expected):
    assert format_time(seconds) == expected


def test_format_time_without_decimals():
    assert format_time(300, 0) == "5:00"


@pytest.mark.parametrize(("seconds", "expected"), [(4.5, "4,50 s"), (12.04, "12,0 s"), (300, "5:00")])
def test_format_span(seconds, expected):
    assert format_span(seconds) == expected


@pytest.mark.parametrize(("seconds", "expected"), [(10.4, "10 s"), (0.3, "0 s"), (59.6, "1:00"), (300.2, "5:00"), (3725, "62:05")])
def test_format_length(seconds, expected):
    from emzon.timefmt import format_length

    assert format_length(seconds) == expected
