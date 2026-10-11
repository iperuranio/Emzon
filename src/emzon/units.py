"""Sizes, frame rates and codecs as the interface shows them."""

CODECS = {"h264": "H.264", "hevc": "HEVC", "av1": "AV1", "vp9": "VP9", "mpeg4": "MPEG-4", "prores": "ProRes"}


def format_size(size: int) -> str:
    if size < 1000**2:
        return f"{max(1, round(size / 1000))} KB"
    if size < 1000**3:
        return f"{round(size / 1000**2)} MB"
    return f"{size / 1000**3:.1f} GB".replace(".", ",")


def format_fps(fps: float) -> str:
    rounded = round(fps)
    if abs(fps - rounded) < 0.01:
        return f"{rounded} fps"
    return f"{fps:.2f} fps".replace(".", ",")


def codec_name(codec: str) -> str:
    return CODECS.get(codec, codec.upper() or "?")
