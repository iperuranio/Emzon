"""Unpacks the third-party Windows binaries into vendor/ after checking their SHA-256.

    gh release download vendor-1 --dir packaging/downloads
    python packaging/fetch_vendor.py packaging/downloads

The archives are listed with their hashes in packaging/vendor.json. A missing
archive or a hash that does not match stops the build.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "packaging" / "vendor.json"
VENDOR = ROOT / "vendor"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract(archive: Path, into: Path) -> None:
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(into)
    elif archive.suffix == ".7z":
        subprocess.run(["7z", "x", "-y", f"-o{into}", str(archive)], check=True, stdout=subprocess.DEVNULL)
    else:
        raise SystemExit(f"unknown archive type: {archive.name}")


def install(entry: dict, downloads: Path) -> None:
    archive = downloads / entry["name"]
    if not archive.is_file():
        raise SystemExit(f"missing {archive}")
    actual = sha256(archive)
    if actual != entry["sha256"]:
        raise SystemExit(f"{archive.name}: SHA-256 {actual} does not match {entry['sha256']}")
    with tempfile.TemporaryDirectory() as temporary:
        unpacked = Path(temporary)
        extract(archive, unpacked)
        members = [p.relative_to(unpacked).as_posix() for p in unpacked.rglob("*") if p.is_file()]
        for pattern, target in entry["files"].items():
            matches = [m for m in members if fnmatch.fnmatch(m, pattern)]
            if not matches:
                raise SystemExit(f"{archive.name}: nothing matches {pattern}")
            for member in matches:
                destination = VENDOR / target / Path(member).name if target == "." else VENDOR / target
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(unpacked / member, destination)
                print(f"{member} -> {destination.relative_to(ROOT)}")


def main() -> int:
    downloads = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "packaging" / "downloads"
    manifest = json.loads(MANIFEST.read_text())
    shutil.rmtree(VENDOR, ignore_errors=True)
    for entry in manifest["archives"]:
        install(entry, downloads)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
