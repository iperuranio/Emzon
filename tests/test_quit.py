import os
import subprocess
import sys
import time

import pytest
from PySide6.QtCore import QCoreApplication

from emzon.single import InstanceServer

TIMEOUT = 20


@pytest.fixture
def isolated(monkeypatch):
    """A channel name of its own, so a real Emzon on this machine is never touched."""
    name = f"emzon-test-{os.getpid()}-{time.monotonic_ns()}"
    monkeypatch.setenv("USERNAME", name)
    monkeypatch.setenv("USER", name)
    return QCoreApplication.instance() or QCoreApplication([])


def quit_command() -> subprocess.Popen:
    # A platform that does not exist: if --quit tried to open a window, Qt would abort.
    env = {**os.environ, "QT_QPA_PLATFORM": "no-such-platform"}
    return subprocess.Popen([sys.executable, "-m", "emzon", "--quit"], env=env)


def wait_for(process: subprocess.Popen) -> float:
    started = time.monotonic()
    while process.poll() is None:
        QCoreApplication.processEvents()
        assert time.monotonic() - started < TIMEOUT, "--quit did not exit"
        time.sleep(0.01)
    for _ in range(20):
        QCoreApplication.processEvents()
        time.sleep(0.01)
    return time.monotonic() - started


def open_copy(can_quit: bool):
    server = InstanceServer(lambda: can_quit)
    asked = []
    server.quit_accepted.connect(lambda: asked.append(True))
    assert server.listen()
    return server, asked


def test_with_no_copy_open_quit_just_exits(isolated):
    process = quit_command()
    wait_for(process)
    assert process.returncode == 0


def test_an_idle_copy_is_told_to_close(isolated):
    server, asked = open_copy(can_quit=True)
    process = quit_command()
    wait_for(process)
    server.close()
    assert process.returncode == 0
    assert asked == [True]


def test_a_copy_that_is_exporting_stays_open(isolated):
    server, asked = open_copy(can_quit=False)
    process = quit_command()
    wait_for(process)
    server.close()
    assert process.returncode == 0
    assert asked == []


def test_the_release_manifest_declares_the_flag_the_app_handles():
    import json
    from pathlib import Path

    from emzon.app import QUIT_FLAG

    manifest = json.loads((Path(__file__).resolve().parents[1] / ".nexus" / "products.json").read_text())
    for product in manifest["products"]:
        for platform in product["platforms"].values():
            assert platform.get("quit") == QUIT_FLAG
