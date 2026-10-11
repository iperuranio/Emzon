"""Filter graphs that play every audio track at once, each at its own volume.

mpv sends a single audio stream through its filter chain. The tracks are
therefore merged into one multichannel stream by `lavfi-complex`, then split
back into stereo pairs inside a labelled `af` graph where each pair has a
named volume filter that `af-command` can change during playback.
"""

from __future__ import annotations

from collections.abc import Sequence

MIX_LABEL = "mix"


def volume_filter(position: int) -> str:
    return f"volume@t{position + 1}"


def complex_graph(track_count: int) -> str:
    if track_count <= 0:
        return ""
    stereo = [f"[aid{i}]aformat=channel_layouts=stereo[s{i}]" for i in range(1, track_count + 1)]
    if track_count == 1:
        return "[aid1]aformat=channel_layouts=stereo[ao]"
    inputs = "".join(f"[s{i}]" for i in range(1, track_count + 1))
    return ";".join(stereo) + f";{inputs}amerge=inputs={track_count}[ao]"


def mix_filter(gains: Sequence[float]) -> str:
    count = len(gains)
    if count == 0:
        return ""
    if count == 1:
        return f"@{MIX_LABEL}:lavfi=[{volume_filter(0)}={gains[0]:.3f}]"
    split = f"asplit={count}" + "".join(f"[i{i}]" for i in range(count))
    tracks = [
        f"[i{i}]pan=stereo|c0=c{2 * i}|c1=c{2 * i + 1},{volume_filter(i)}={gain:.3f}[m{i}]"
        for i, gain in enumerate(gains)
    ]
    mix = "".join(f"[m{i}]" for i in range(count)) + f"amix=inputs={count}:normalize=0"
    return f"@{MIX_LABEL}:lavfi=[{split};{';'.join(tracks)};{mix}]"
