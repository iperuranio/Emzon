import json
import shutil
import subprocess
from pathlib import Path

import pytest

from emzon.export.jobs import (
    AudioFormat,
    Kind,
    Request,
    command,
    destination,
    mix_graph,
    parse_progress,
)


def test_copy_goes_next_to_the_original(tmp_path):
    source = tmp_path / "Valorant 2026.10.08.mp4"
    assert destination(source, Kind.VIDEO, AudioFormat.MP3, None) == tmp_path / "Valorant 2026.10.08_edited.mp4"


def test_taken_names_get_a_number(tmp_path):
    source = tmp_path / "clip.mp4"
    (tmp_path / "clip_edited.mp4").touch()
    queued = {tmp_path / "clip_edited (2).mp4"}
    assert destination(source, Kind.VIDEO, AudioFormat.MP3, None, queued) == tmp_path / "clip_edited (3).mp4"


def test_audio_uses_its_own_extension_and_folder(tmp_path):
    source = tmp_path / "clip.mp4"
    folder = tmp_path / "sounds"
    assert destination(source, Kind.AUDIO, AudioFormat.WAV, folder) == folder / "clip_edited.wav"


def test_unusual_containers_become_mp4(tmp_path):
    assert destination(tmp_path / "clip.webm", Kind.VIDEO, AudioFormat.MP3, None).suffix == ".mp4"
    assert destination(tmp_path / "clip.MKV", Kind.VIDEO, AudioFormat.MP3, None).suffix == ".mkv"


def test_mix_graph_matches_the_player():
    assert mix_graph([1.0]) == "[0:a:0]aformat=sample_rates=48000:channel_layouts=stereo,volume=1.000[aout]"
    assert mix_graph([1.0, 0.6]) == (
        "[0:a:0]aformat=sample_rates=48000:channel_layouts=stereo,volume=1.000[a0];"
        "[0:a:1]aformat=sample_rates=48000:channel_layouts=stereo,volume=0.600[a1];"
        "[a0][a1]amix=inputs=2:normalize=0[aout]"
    )


def request(tmp_path, kind=Kind.VIDEO, gains=(1.0, 0.6), codec="h264", fmt=AudioFormat.MP3):
    source = tmp_path / "clip.mp4"
    return Request(source, kind, 252.0, 262.4, gains, codec, destination(source, kind, fmt, None), fmt)


def test_video_command_seeks_then_trims_and_writes_a_partial_file(tmp_path):
    args = command("ffmpeg", request(tmp_path), hardware=True)
    assert args[args.index("-ss") + 1] == "252.000000"
    assert args.index("-ss") < args.index("-i")
    assert args[args.index("-t") + 1] == "10.400000"
    assert args[args.index("-c:v") + 1] == "h264_nvenc"
    assert args[-1] == str(tmp_path / "clip_edited.partial.mp4")


def test_software_encoder_per_codec(tmp_path):
    for codec, encoder in (("h264", "libx264"), ("hevc", "libx265"), ("av1", "libsvtav1"), ("vp9", "libx264")):
        args = command("ffmpeg", request(tmp_path, codec=codec), hardware=False)
        assert args[args.index("-c:v") + 1] == encoder


def test_audio_command_drops_the_video(tmp_path):
    args = command("ffmpeg", request(tmp_path, Kind.AUDIO, fmt=AudioFormat.OGG), hardware=True)
    assert "-vn" in args and "-c:v" not in args
    assert args[args.index("-c:a") + 1] == "libvorbis"
    assert args[-1].endswith("clip_edited.partial.ogg")


def test_silent_clip_exports_video_without_audio(tmp_path):
    args = command("ffmpeg", request(tmp_path, gains=()), hardware=False)
    assert "-filter_complex" not in args and "[aout]" not in args


def test_audio_export_needs_audio(tmp_path):
    with pytest.raises(ValueError):
        command("ffmpeg", request(tmp_path, Kind.AUDIO, gains=()), hardware=False)


@pytest.mark.parametrize(
    ("line", "expected"),
    [("out_time_us=5200000", 0.5), ("out_time_ms=10400000", 1.0), ("progress=continue", None), ("out_time_us=N/A", None)],
)
def test_parse_progress(line, expected):
    assert parse_progress(line, 10.4) == expected


FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


@pytest.mark.skipif(not (FFMPEG and FFPROBE), reason="needs ffmpeg and ffprobe")
@pytest.mark.parametrize("kind", [Kind.VIDEO, Kind.AUDIO])
def test_real_export_is_trimmed_to_the_selection(tmp_path, kind):
    source = tmp_path / "clip.mp4"
    subprocess.run(
        [FFMPEG, "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=6",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
         "-f", "lavfi", "-i", "sine=frequency=880:duration=6",
         "-map", "0:v", "-map", "1:a", "-map", "2:a", "-c:v", "libx264", "-c:a", "aac", str(source)],
        check=True,
    )
    job = Request(source, kind, 1.5, 4.0, (1.0, 0.5), "h264", destination(source, kind, AudioFormat.MP3, None))
    subprocess.run(command(FFMPEG, job, hardware=False), check=True, capture_output=True)
    info = json.loads(subprocess.run(
        [FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(job.partial)],
        check=True, capture_output=True,
    ).stdout)
    assert float(info["format"]["duration"]) == pytest.approx(2.5, abs=0.06)
    audio = [s for s in info["streams"] if s["codec_type"] == "audio"]
    video = [s for s in info["streams"] if s["codec_type"] == "video"]
    assert len(audio) == 1 and audio[0]["channels"] == 2
    assert len(video) == (1 if kind is Kind.VIDEO else 0)


def test_gpu_decoding_only_in_the_hardware_attempt(tmp_path):
    hardware = command("ffmpeg", request(tmp_path), hardware=True)
    software = command("ffmpeg", request(tmp_path), hardware=False)
    audio = command("ffmpeg", request(tmp_path, Kind.AUDIO), hardware=True)
    assert hardware[hardware.index("-hwaccel") + 1] == "auto"
    assert hardware.index("-hwaccel") < hardware.index("-i")
    assert "-hwaccel" not in software and "-hwaccel" not in audio
