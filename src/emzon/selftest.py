"""`Emzon.exe --self-test report.json`: checks a packaged build without opening a window.

Every check runs even if an earlier one fails; the exit code is 0 only when all pass.
"""

from __future__ import annotations

import json
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

from PySide6.QtGui import QFontDatabase, QGuiApplication

from emzon.export.jobs import AudioFormat, Kind, Request, command, destination
from emzon.media.probe import probe
from emzon.media.tools import find_tool, run
from emzon.ui import theme


def _tool_version(name: str) -> str:
    result = run([find_tool(name), "-version"], timeout=30)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    return result.stdout.decode(errors="replace").splitlines()[0]


def _libmpv() -> str:
    import mpv

    player = mpv.MPV(vo="null", ao="null")
    try:
        return str(player.mpv_version)
    finally:
        player.terminate()


def _fonts() -> str:
    theme.load_fonts()
    families = set(QFontDatabase.families())
    missing = {theme.UI_FAMILY, theme.MONO_FAMILY} - families
    if missing:
        raise RuntimeError(f"missing fonts: {', '.join(sorted(missing))}")
    return "Geist, Geist Mono"


def _export_round_trip() -> str:
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "clip.mp4"
        made = run([
            find_tool("ffmpeg"), "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=3",
            "-f", "lavfi", "-i", "sine=duration=3", "-f", "lavfi", "-i", "sine=frequency=880:duration=3",
            "-map", "0:v", "-map", "1:a", "-map", "2:a", "-c:v", "libx264", "-c:a", "aac", source,
        ], timeout=60)
        if made.returncode != 0:
            raise RuntimeError(made.stderr.decode(errors="replace"))
        clip = probe(source)
        if len(clip.audio) != 2:
            raise RuntimeError(f"expected 2 audio tracks, found {len(clip.audio)}")
        outcomes = []
        for kind in (Kind.VIDEO, Kind.AUDIO):
            request = Request(source, kind, 0.5, 2.5, (1.0, 0.5), clip.video_codec,
                              destination(source, kind, AudioFormat.MP3, None))
            result = run(command(find_tool("ffmpeg"), request, hardware=False), timeout=120)
            if result.returncode != 0 or not request.partial.is_file():
                raise RuntimeError(result.stderr.decode(errors="replace") or f"{kind.value} export failed")
            outcomes.append(f"{kind.value} {probe_duration(request.partial):.2f} s")
        return ", ".join(outcomes)


def probe_duration(path: Path) -> float:
    result = run([find_tool("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], timeout=30)
    return float(result.stdout.decode().strip())


CHECKS: dict[str, Callable[[], str]] = {
    "ffmpeg": lambda: _tool_version("ffmpeg"),
    "ffprobe": lambda: _tool_version("ffprobe"),
    "libmpv": _libmpv,
    "fonts": _fonts,
    "export": _export_round_trip,
}


def run_checks(report: Path) -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    results: dict[str, dict[str, str]] = {}
    for name, check in CHECKS.items():
        try:
            results[name] = {"ok": "yes", "detail": check()}
        except Exception as error:  # noqa: BLE001  the report must list every failure
            results[name] = {"ok": "no", "detail": f"{type(error).__name__}: {error}"}
    report.write_text(json.dumps(results, indent=2), encoding="utf-8")
    app.quit()
    return 0 if all(r["ok"] == "yes" for r in results.values()) else 1
