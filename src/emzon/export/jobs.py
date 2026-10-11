"""Turning a trimmed clip into an FFmpeg command line."""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

EDITED_SUFFIX = "_edited"
PARTIAL_SUFFIX = ".partial"
VIDEO_CONTAINERS = {".mp4", ".mov", ".m4v", ".mkv"}
DEFAULT_CONTAINER = ".mp4"


class Kind(Enum):
    VIDEO = "video"
    AUDIO = "audio"


class AudioFormat(Enum):
    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"

    @property
    def extension(self) -> str:
        return f".{self.value}"

    @property
    def codec(self) -> list[str]:
        return {
            AudioFormat.MP3: ["-c:a", "libmp3lame", "-q:a", "0"],
            AudioFormat.WAV: ["-c:a", "pcm_s16le"],
            AudioFormat.OGG: ["-c:a", "libvorbis", "-q:a", "6"],
        }[self]


@dataclass(frozen=True)
class Encoder:
    name: str
    options: tuple[str, ...]


HARDWARE = {
    "h264": Encoder("h264_nvenc", ("-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "19", "-b:v", "0", "-pix_fmt", "yuv420p")),
    "hevc": Encoder("hevc_nvenc", ("-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "21", "-b:v", "0")),
    "av1": Encoder("av1_nvenc", ("-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "28", "-b:v", "0")),
}
SOFTWARE = {
    "h264": Encoder("libx264", ("-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p")),
    "hevc": Encoder("libx265", ("-preset", "fast", "-crf", "20")),
    "av1": Encoder("libsvtav1", ("-preset", "8", "-crf", "30")),
}


def target_codec(source_codec: str) -> str:
    return source_codec if source_codec in HARDWARE else "h264"


@dataclass(frozen=True)
class Request:
    source: Path
    kind: Kind
    start: float
    end: float
    gains: tuple[float, ...]
    video_codec: str
    destination: Path
    audio_format: AudioFormat = AudioFormat.MP3
    replace_original: bool = False

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def partial(self) -> Path:
        return self.destination.with_name(self.destination.stem + PARTIAL_SUFFIX + self.destination.suffix)


def video_extension(source: Path) -> str:
    suffix = source.suffix.lower()
    return suffix if suffix in VIDEO_CONTAINERS else DEFAULT_CONTAINER


def destination(
    source: Path,
    kind: Kind,
    audio_format: AudioFormat,
    folder: Path | None,
    taken: Collection[Path] = (),
) -> Path:
    """`<name>_edited.<ext>`, or `<name>_edited (2).<ext>` and so on when the name is in use."""
    extension = video_extension(source) if kind is Kind.VIDEO else audio_format.extension
    directory = folder or source.parent
    base = source.stem + EDITED_SUFFIX
    candidate = directory / f"{base}{extension}"
    number = 2
    while candidate.exists() or candidate in taken:
        candidate = directory / f"{base} ({number}){extension}"
        number += 1
    return candidate


def mix_graph(gains: Sequence[float]) -> str:
    """Every audio track to stereo at its gain, then summed: the same mix the player plays."""
    chains = [
        f"[0:a:{i}]aformat=sample_rates=48000:channel_layouts=stereo,volume={gain:.3f}[a{i}]"
        for i, gain in enumerate(gains)
    ]
    if len(gains) == 1:
        return chains[0].replace("[a0]", "[aout]")
    inputs = "".join(f"[a{i}]" for i in range(len(gains)))
    return ";".join(chains) + f";{inputs}amix=inputs={len(gains)}:normalize=0[aout]"


def command(ffmpeg: Path | str, request: Request, hardware: bool) -> list[str]:
    args = [
        str(ffmpeg), "-hide_banner", "-nostdin", "-y", "-v", "error",
        "-progress", "pipe:1", "-nostats",
    ]
    if hardware and request.kind is Kind.VIDEO:
        args += ["-hwaccel", "auto"]
    args += [
        "-ss", f"{request.start:.6f}", "-i", str(request.source),
        "-t", f"{request.duration:.6f}",
    ]
    if request.gains:
        args += ["-filter_complex", mix_graph(request.gains)]

    if request.kind is Kind.AUDIO:
        if not request.gains:
            raise ValueError("no audio to export")
        args += ["-map", "[aout]", "-vn", *request.audio_format.codec]
    else:
        codec = target_codec(request.video_codec)
        encoder = (HARDWARE if hardware else SOFTWARE)[codec]
        args += ["-map", "0:v:0", "-c:v", encoder.name, *encoder.options]
        if request.gains:
            args += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
        if request.destination.suffix.lower() in {".mp4", ".mov", ".m4v"}:
            args += ["-movflags", "+faststart"]
        args += ["-avoid_negative_ts", "make_zero"]

    args += ["-map_chapters", "-1", str(request.partial)]
    return args


def parse_progress(line: str, duration: float) -> float | None:
    """Fraction done from one line of `-progress` output, if the line carries it."""
    key, _, value = line.strip().partition("=")
    if key not in ("out_time_us", "out_time_ms") or not value.isdigit() or duration <= 0:
        return None
    return min(1.0, int(value) / 1_000_000 / duration)
