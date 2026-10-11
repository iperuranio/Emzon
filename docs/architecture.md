# Architecture

## Stack

- **Python 3.12+** with **PySide6** (Qt Widgets) for the interface.
- **libmpv**, through `python-mpv`, for playback.
- **FFmpeg** and **FFprobe** executables for probing, waveforms, thumbnails and export.

Windows 10 and 11 (x64) are the target. Everything except NVENC encoding also runs on macOS, which keeps the app easy to develop and test.

## Modules

```
src/emzon/
  app.py              entry point
  window.py           main window, key bindings, wiring
  tasks.py            background work with results delivered on the UI thread
  timefmt.py          time and duration formatting
  settings.py         persisted preferences
  media/
    probe.py          ffprobe → Clip (duration, frame rate, codecs, audio tracks)
    waveform.py       per-track peak data
    thumbnails.py     frames for the video lane
    tools.py          locating and running ffmpeg and ffprobe
  player/
    mpv_widget.py     libmpv render API inside a QOpenGLWidget
    audio_graph.py    filter graphs for mixing tracks
  timeline/
    model.py          view range, playhead, cut points and their rules
    view.py           painting and mouse handling
  export/
    jobs.py           building ffmpeg command lines
    queue.py          background queue
  ui/
    strings.py        every visible string
    theme.py          design tokens
    icons.py          stroke icons
    widgets.py        buttons shared by the window
    fonts/            Geist and Geist Mono (SIL Open Font License)
```

`timeline/model.py` and `export/jobs.py` hold the rules that matter most and depend on nothing in Qt, so they are covered by plain unit tests.

## Playback

The video is drawn by libmpv's render API into a `QOpenGLWidget`, with hardware decoding (`hwdec=auto-safe`). Qt owns the window, so the same code runs on both platforms.

### Mixing audio tracks

mpv plays one audio stream, while a ShadowPlay file can carry several. The tracks are joined and split again around the regular audio filter chain:

1. `lavfi-complex` converts every track to stereo and merges them into one multichannel stream on the `ao` pad.
2. The `af` chain holds a single labelled `lavfi` graph that splits that stream with `pan`, applies a named `volume@tN` filter to each track and mixes them with `amix=normalize=0`.
3. A volume change is an `af-command` addressed to `volume@tN`. It applies to audio already playing, without rebuilding the graph or interrupting playback.

Export builds the same graph in its own `filter_complex`, so what you hear is what gets saved.

## Waveforms and thumbnails

Each audio track is decoded once by FFmpeg to low-rate mono PCM and reduced to a pyramid of peak values, so every zoom level draws from a level of matching resolution. Thumbnails come from keyframes, scaled down, and load lazily for the visible range. Both run in background threads and are cached by file path, size and modification time.

## Export

Jobs run one at a time in a background thread, each as an FFmpeg process.

- **Video:** re-encoded with NVENC in the source codec (`h264_nvenc`, `hevc_nvenc`, `av1_nvenc`) at a quality close to the source. Cuts are frame-accurate: the input is seeked to the head and the output runs for the exact selected duration. Audio tracks are mixed into one stereo track with the current volumes.
- **Audio:** the same mix, encoded to the format chosen in the settings (MP3 by default).
- If NVENC is not available, the job falls back to software encoding and the queue row says so.
- Replacing the original writes the new file next to it first, then moves the original to the Recycle Bin, then renames the new file.

## Packaging

PyInstaller builds a one-folder app on a GitHub Actions Windows runner (`packaging/emzon.spec`), published as a zip with `version.txt` next to `Emzon.exe`. FFmpeg, FFprobe and libmpv come from exact copies attached to the `vendor-1` release of this repository; `packaging/fetch_vendor.py` checks each archive against the SHA-256 in `packaging/vendor.json` before unpacking it into `vendor/`.

Before packaging, the build checks that FFmpeg has every encoder Emzon uses and runs the test suite with the bundled FFmpeg. After packaging it runs `Emzon.exe --self-test report.json`, which loads libmpv and the fonts and exports a short generated clip, all without opening a window.

A tag `vX.Y.Z` must match `__version__` in `src/emzon/__init__.py`, otherwise the build stops. The release is created with its zip in one step.

On Windows the app keeps a shortcut in `Start Menu\Programs\Metessi` pointing at the running exe, rewritten at start when it is missing or stale, and logs to `%LOCALAPPDATA%\Metessi\Emzon\emzon.log`.

## Performance

- No timers or repaints while the window is hidden or unfocused and not playing.
- Probing, waveforms, thumbnails and exports never run on the UI thread.
- The timeline repaints only what changed. During playback that is the playhead.
