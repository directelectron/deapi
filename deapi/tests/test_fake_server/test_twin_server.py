"""``pydeserver --twin``: the simulated server backed by the de-twin digital twin."""

import socket
import subprocess
import sys
import threading
import time

import numpy as np
import pytest

from deapi.client import Client
from deapi.simulated_server import initialize_server


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_twin_flag_without_the_twin_installed_explains_how_to_get_it(
    monkeypatch, capsys
):
    monkeypatch.setitem(sys.modules, "de_twin", None)  # import de_twin -> ImportError
    monkeypatch.setitem(sys.modules, "de_twin.faces", None)
    monkeypatch.setattr(sys, "argv", ["pydeserver", "--twin"])
    assert initialize_server.main(_free_port()) == 2
    assert 'pip install "deapi[twin]"' in capsys.readouterr().err


def test_twin_server_serves_twin_frames():
    pytest.importorskip("de_twin")
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "-m",
            "deapi.simulated_server.initialize_server",
            str(port),
            "--twin",
            "--camera",
            "DESim",
            "--specimen",
            "Dense Au on holey C",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    lines = []
    started = threading.Event()

    def read():
        for line in proc.stdout:
            lines.append(line)
            if "started" in line:
                started.set()

    threading.Thread(target=read, daemon=True).start()
    try:
        assert started.wait(120), "".join(lines)
        client = Client()
        client.usingMmf = False
        client.connect(port=port)
        assert client["Sensor Size X (pixels)"] == 1024  # the twin's DESim model
        client["Frame Count"] = 2
        client.start_acquisition(1)
        deadline = time.time() + 60
        while client.acquiring and time.time() < deadline:
            time.sleep(0.05)
        image, *_ = client.get_result("singleframe_integrated")
        assert image.shape == (1024, 1024)
        assert np.asarray(image).std() > 0  # a rendered specimen, not a constant
        assert client["Instrument Project Magnification"]  # the twin's column metadata
        client.disconnect()
    finally:
        proc.terminate()
        proc.wait(10)
