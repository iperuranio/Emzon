"""Times as the interface shows them: 4:16,40 and 10,00 s."""


def format_time(seconds: float, decimals: int = 2) -> str:
    seconds = max(0.0, seconds)
    scale = 10**decimals
    total = round(seconds * scale)
    minutes, rest = divmod(total, 60 * scale)
    whole, fraction = divmod(rest, scale)
    text = f"{minutes}:{whole:02d}"
    if decimals:
        text += f",{fraction:0{decimals}d}"
    return text


def format_span(seconds: float) -> str:
    """Compact length for the zoom readout."""
    if seconds < 10:
        return f"{seconds:.2f} s".replace(".", ",")
    if seconds < 60:
        return f"{seconds:.1f} s".replace(".", ",")
    return format_time(seconds, 0)


def format_length(seconds: float) -> str:
    """A length in whole seconds: 10 s under a minute, 4:12 from there on."""
    whole = round(max(0.0, seconds))
    return f"{whole} s" if whole < 60 else format_time(whole, 0)
