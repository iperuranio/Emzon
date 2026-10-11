"""Peak data for drawing audio tracks at any zoom level."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from emzon.media.tools import find_tool, run

SAMPLE_RATE = 8000
PEAK_RATE = 400
DECODE_TIMEOUT = 300


class WaveformError(RuntimeError):
    pass


class Waveform:
    """Peaks at PEAK_RATE per second, plus coarser levels each halving the rate."""

    def __init__(self, peaks: np.ndarray) -> None:
        self.levels = [peaks.astype(np.float32)]
        while len(self.levels[-1]) > 1:
            previous = self.levels[-1]
            if len(previous) % 2:
                previous = np.append(previous, 0.0)
            self.levels.append(previous.reshape(-1, 2).max(axis=1))

    @classmethod
    def from_samples(cls, samples: np.ndarray) -> Waveform:
        block = SAMPLE_RATE // PEAK_RATE
        usable = len(samples) - len(samples) % block
        magnitude = np.abs(samples[:usable].astype(np.float32) / 32768.0)
        if usable == 0:
            return cls(np.zeros(1, dtype=np.float32))
        return cls(magnitude.reshape(-1, block).max(axis=1))

    @property
    def duration(self) -> float:
        return len(self.levels[0]) / PEAK_RATE

    def peaks(self, start: float, end: float, count: int) -> np.ndarray:
        """The loudest value in each of `count` equal slices of [start, end]."""
        if count <= 0 or end <= start:
            return np.zeros(max(count, 0), dtype=np.float32)
        edges = start + (end - start) * np.arange(count + 1) / count
        centers = (edges[:-1] + edges[1:]) / 2
        outside = (edges[1:] <= 0) | (edges[:-1] >= self.duration)
        rate = count / (end - start)

        if rate >= PEAK_RATE:
            base = self.levels[0]
            values = np.interp(centers * PEAK_RATE, np.arange(len(base)), base, left=0.0, right=0.0)
        else:
            level_index = min(int(np.log2(PEAK_RATE / rate)), len(self.levels) - 1)
            level = self.levels[level_index]
            level_rate = PEAK_RATE / 2**level_index
            index = np.clip((edges * level_rate).astype(np.int64), 0, len(level) - 1)
            values = np.maximum.reduceat(level, index[:-1])
            single = index[:-1] >= index[1:]
            values[single] = level[index[:-1][single]]

        values = values.astype(np.float32)
        values[outside] = 0.0
        return values


def load_waveform(path: Path, position: int) -> Waveform:
    result = run(
        [
            find_tool("ffmpeg"), "-v", "error", "-i", path,
            "-map", f"0:a:{position}", "-ac", "1", "-ar", str(SAMPLE_RATE),
            "-f", "s16le", "-",
        ],
        timeout=DECODE_TIMEOUT,
    )
    if result.returncode != 0:
        raise WaveformError(result.stderr.decode(errors="replace").strip() or "ffmpeg failed")
    return Waveform.from_samples(np.frombuffer(result.stdout, dtype=np.int16))
