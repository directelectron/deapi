import sys
import pytest
import pathlib
from xprocess import ProcessStarter
import sys

import numpy as np

from deapi.client import Client


def pytest_addoption(parser):
    parser.addoption(
        "--server",
        action="store_true",
        default=False,
        help="If a remote server is running",
    )
    parser.addoption(
        "--host", action="store", default="127.0.0.1", help="host to connect to"
    )
    parser.addoption("--port", action="store", default=13240, help="port to connect to")


@pytest.fixture(scope="module")
def client(xprocess, request):
    if request.config.getoption("--server"):
        c = Client()
        if request.config.getoption("--host") != "127.0.0.1" or sys.platform != "win32":
            c.usingMmf = False
        c.connect(
            host=request.config.getoption("--host"),
            port=request.config.getoption("--port"),
        )
        yield c
        c.disconnect()
        return
    else:
        port = np.random.randint(5000, 9999)
        curdir = pathlib.Path(__file__).parent.parent

        class Starter(ProcessStarter):
            timeout = 20
            pattern = "started"
            args = [
                sys.executable,
                curdir / "simulated_server/initialize_server.py",
                port,
            ]

        xprocess.ensure("server-%s" % port, Starter)
        c = Client()
        c.usingMmf = False
        c.connect(port=port)
        yield c
        xprocess.getinfo("server-%s" % port).terminate()
