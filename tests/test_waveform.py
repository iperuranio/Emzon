import numpy as np
import pytest

from emzon.media.waveform import PEAK_RATE, SAMPLE_RATE, Waveform


def burst_at(second: float, length: float = 10.0) -> Waveform:
    samples = np.zeros(int(length * SAMPLE_RATE), dtype=np.int16)
    start = int(second * SAMPLE_RATE)
    samples[start:start + SAMPLE_RATE // 10] = 16384
    return Waveform.from_samples(samples)


def test_duration_follows_the_samples():
    assert burst_at(1).duration == pytest.approx(10)


def test_a_burst_shows_up_in_the_right_slice_at_every_zoom():
    wave = burst_at(6.0)
    for count in (10, 100, 1000, 20000):
        peaks = wave.peaks(0, 10, count)
        loudest = int(np.argmax(peaks))
        assert loudest * 10 / count == pytest.approx(6.0, abs=10 / count + 0.1)
        assert peaks.max() == pytest.approx(0.5, abs=0.01)


def test_slices_outside_the_file_are_silent():
    wave = burst_at(0.0)
    peaks = wave.peaks(-5, 0, 50)
    assert not peaks.any()


def test_deep_zoom_interpolates_between_peaks():
    wave = burst_at(5.0)
    peaks = wave.peaks(5.0, 5.05, 400)
    assert len(peaks) == 400
    assert peaks.max() > 0.4


def test_levels_halve_down_to_one_value():
    wave = burst_at(3.0)
    assert len(wave.levels[0]) == 10 * PEAK_RATE
    assert len(wave.levels[-1]) == 1
    assert wave.levels[-1][0] == pytest.approx(0.5, abs=0.01)
