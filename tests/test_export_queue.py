import shutil
import subprocess
import time
from pathlib import Path

import pytest

from emzon.export import queue as queue_module
from emzon.export.jobs import AudioFormat, Kind, Request, destination
from emzon.export.queue import ExportQueue, State

FFMPEG = shutil.which("ffmpeg")
pytestmark = pytest.mark.skipif(not FFMPEG, reason="needs ffmpeg")


@pytest.fixture
def clip(tmp_path) -> Path:
    path = tmp_path / "clip.mp4"
    subprocess.run(
        [FFMPEG, "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=4",
         "-f", "lavfi", "-i", "sine=duration=4", "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-c:a", "aac", str(path)],
        check=True,
    )
    return path


@pytest.fixture
def export_queue():
    q = ExportQueue(ffmpeg=lambda: Path(FFMPEG))
    yield q
    q.shutdown()


def wait(job, timeout=60):
    end = time.monotonic() + timeout
    while job.state.active and job.state is not State.FINISHING:
        assert time.monotonic() < end, "export did not finish"
        time.sleep(0.05)


def video_request(clip, **changes):
    values = dict(
        source=clip, kind=Kind.VIDEO, start=1.0, end=3.0, gains=(1.0,), video_codec="h264",
        destination=destination(clip, Kind.VIDEO, AudioFormat.MP3, None),
    )
    values.update(changes)
    return Request(**values)


def test_export_lands_under_its_final_name(clip, export_queue):
    job = export_queue.add(video_request(clip))
    wait(job)
    assert job.state is State.DONE, job.error
    assert job.output.exists() and not job.request.partial.exists()
    assert job.progress == 1.0


def test_without_nvenc_the_job_falls_back_to_software(clip, export_queue):
    encoders = subprocess.run([FFMPEG, "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    if "h264_nvenc" in encoders:
        pytest.skip("this FFmpeg has NVENC")
    job = export_queue.add(video_request(clip))
    wait(job)
    assert job.state is State.DONE and job.software


def test_names_in_the_queue_are_reserved(clip, export_queue):
    first = export_queue.add(video_request(clip))
    second_destination = destination(clip, Kind.VIDEO, AudioFormat.MP3, None, export_queue.reserved())
    assert second_destination != first.output
    wait(first)


def test_cancelling_removes_the_partial_file(clip, export_queue):
    job = export_queue.add(video_request(clip, end=4.0))
    export_queue.cancel(job)
    wait(job)
    time.sleep(0.3)
    assert job.state is State.CANCELLED
    assert not job.request.partial.exists() and not job.output.exists()


def test_a_broken_source_fails_with_a_reason(tmp_path, export_queue):
    broken = tmp_path / "broken.mp4"
    broken.write_bytes(b"not a video")
    job = export_queue.add(video_request(broken, destination=tmp_path / "broken_edited.mp4"))
    wait(job)
    assert job.state is State.FAILED
    assert job.error


def test_replacing_trashes_the_original_and_takes_its_place(clip, export_queue, monkeypatch):
    trashed = []
    monkeypatch.setattr(queue_module, "send2trash", lambda path: (trashed.append(path), Path(path).unlink()))
    original_size = clip.stat().st_size
    job = export_queue.add(video_request(clip, destination=clip, replace_original=True))
    wait(job)
    assert job.state is State.FINISHING
    export_queue.finish_replace(job)
    assert job.state is State.DONE
    assert trashed == [clip]
    assert clip.exists() and clip.stat().st_size != original_size


def test_when_the_original_cannot_be_trashed_the_export_is_kept_as_a_copy(clip, export_queue, monkeypatch):
    def refuse(path):
        raise OSError("in use")

    monkeypatch.setattr(queue_module, "send2trash", refuse)
    job = export_queue.add(video_request(clip, destination=clip, replace_original=True))
    wait(job)
    export_queue.finish_replace(job)
    assert job.state is State.DONE and job.kept_original
    assert job.output.name == "clip_edited.mp4" and job.output.exists()
