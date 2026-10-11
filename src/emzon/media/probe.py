"""Reading what a clip contains."""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from emzon.media.tools import find_tool, run

PROBE_TIMEOUT = 30


class ProbeError(RuntimeError):
    pass


@dataclass(frozen=True)
class AudioTrack:
    position: int
    channels: int
    title: str | None


@dataclass(frozen=True)
class Clip:
    path: Path
    duration: float
    fps: float
    width: int
    height: int
    video_codec: str
    audio: tuple[AudioTrack, ...]


def probe(path: Path) -> Clip:
    result = run(
        [find_tool("ffprobe"), "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        timeout=PROBE_TIMEOUT,
    )
    if result.returncode != 0:
        raise ProbeError(result.stderr.decode(errors="replace").strip() or "ffprobe failed")
    return parse_probe(json.loads(result.stdout), path)


def parse_probe(data: dict, path: Path) -> Clip:
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video" and not _is_cover(s)), None)
    if video is None:
        raise ProbeError("no video stream")

    duration = _float(data.get("format", {}).get("duration")) or _float(video.get("duration"))
    if not duration or duration <= 0:
        raise ProbeError("unknown duration")

    audio = tuple(
        AudioTrack(
            position=position,
            channels=int(stream.get("channels") or 2),
            title=(stream.get("tags") or {}).get("title") or None,
        )
        for position, stream in enumerate(s for s in streams if s.get("codec_type") == "audio")
    )
    return Clip(
        path=path,
        duration=duration,
        fps=_rate(video.get("avg_frame_rate")) or _rate(video.get("r_frame_rate")) or 60.0,
        width=int(video.get("width") or 0),
        height=int(video.get("height") or 0),
        video_codec=video.get("codec_name", ""),
        audio=audio,
    )


def _is_cover(stream: dict) -> bool:
    return bool((stream.get("disposition") or {}).get("attached_pic"))


def _float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _rate(value: object) -> float | None:
    try:
        rate = Fraction(str(value))
    except (ValueError, ZeroDivisionError):
        return None
    return float(rate) if rate > 0 else None
