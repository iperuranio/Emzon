# PyInstaller build of the Windows app: pyinstaller packaging/emzon.spec
from pathlib import Path

root = Path(SPECPATH).parent
vendor = root / "vendor"
if not (vendor / "ffmpeg.exe").is_file() or not (vendor / "mpv-2.dll").is_file():
    raise SystemExit("vendor/ is incomplete: run packaging/fetch_vendor.py first")

a = Analysis(
    [str(root / "src" / "emzon" / "__main__.py")],
    pathex=[str(root / "src")],
    datas=[
        (str(root / "src" / "emzon" / "ui" / "fonts"), "emzon/ui/fonts"),
        (str(root / "src" / "emzon" / "ui" / "icon.png"), "emzon/ui"),
        (str(vendor), "vendor"),
        (str(root / "LICENSE"), "."),
        (str(root / "THIRD_PARTY.md"), "."),
    ],
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore", "PySide6.QtQuick3D"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Emzon",
    console=False,
    icon=str(root / "packaging" / "icon.ico"),
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Emzon", upx=False)
