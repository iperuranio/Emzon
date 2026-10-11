"""Draws the app icon and writes it in every format the build needs.

    python packaging/make_icon.py
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPainterPath

ROOT = Path(__file__).resolve().parents[1]
ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def draw(size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 1024, size / 1024)

    tile = QPainterPath()
    tile.addRoundedRect(QRectF(32, 32, 960, 960), 220, 220)
    p.fillPath(tile, QColor("#17131F"))

    bar = QRectF(160, 412, 704, 200)
    track = QPainterPath()
    track.addRoundedRect(bar, 100, 100)
    p.save()
    p.setClipPath(track)
    p.fillRect(QRectF(bar.left(), bar.top(), 420, bar.height()), QColor("#3B3450"))
    p.fillRect(QRectF(bar.left() + 420, bar.top(), bar.width() - 420, bar.height()), QColor("#9B7BFF"))
    p.restore()

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#ECE8F4"))
    p.drawRoundedRect(QRectF(bar.left() + 420 - 22, 300, 44, 424), 22, 22)
    p.end()
    return image


def png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def write_ico(path: Path, sizes: tuple[int, ...]) -> None:
    images = [png_bytes(draw(size)) for size in sizes]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    for size, data in zip(sizes, images):
        side = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    path.write_bytes(header + entries + b"".join(images))


def main() -> int:
    QGuiApplication(sys.argv)
    draw(1024).save(str(ROOT / "packaging" / "icon.png"))
    draw(256).save(str(ROOT / "src" / "emzon" / "ui" / "icon.png"))
    write_ico(ROOT / "packaging" / "icon.ico", ICO_SIZES)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
