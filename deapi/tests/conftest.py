import sys
import time

import pytest
import pathlib
from xprocess import ProcessStarter
import sys

import numpy as np

from deapi.client import Client


import psutil


def close_port(port):
    for conn in psutil.net_connections(kind="inet"):
        if conn.laddr.port == port:
            print(f"Closing port {port} by terminating PID {conn.pid}")
            process = psutil.Process(conn.pid)
            process.terminate()


# Modifying pytest run options
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
    parser.addoption(
        "--speed",
        action="store_true",
        default=False,
        help="Test the speed of certain operations",
    )
    parser.addoption(
        "--engineering", action="store", default="", help="Run engineering mode"
    )
    parser.addoption(
        "--examples",
        action="store_true",
        default=False,
        help="Run examples tests",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "server: mark tests that require the full DEServer"
    )
    config.addinivalue_line(
        "markers", "speed: mark tests that measure the speed of the DEServer"
    )
    config.addinivalue_line(
        "markers", "examples: mark tests that run examples from the DEAPI documentation"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--server"):
        # Do not skip server tests
        return
    else:  # pragma: no cover
        skip_server = pytest.mark.skip(reason="need --server option to run")
        for item in items:
            if "server" in item.keywords:
                item.add_marker(skip_server)

    if config.getoption("--examples"):
        # Do not skip examples tests
        return
    else:  # pragma: no cover
        skip_examples = pytest.mark.skip(reason="need --examples option to run")
        for item in items:
            if "examples" in item.keywords:
                item.add_marker(skip_examples)

    if config.getoption("--engineering") and config.getoption("--engineering") != "":
        # Do not skip engineering tests
        return
    else:  # pragma: no cover
        skip_engineering = pytest.mark.skip(reason="need --engineering option to run")
        for item in items:
            if "engineering" in item.keywords:
                item.add_marker(skip_engineering)

    if config.getoption("--speed"):
        # Do not skip speed tests
        return
    else:  # pragma: no cover
        skip_speed = pytest.mark.skip(reason="need --speed option to run")
        for item in items:
            if "speed" in item.keywords:
                item.add_marker(skip_speed)


@pytest.fixture(scope="function")
def server(xprocess, request):
    port = 13240
    if not request.config.getoption("--server"):
        port = 13240
        close_port(port)

        curdir = pathlib.Path(__file__).parent.parent

        class Starter(ProcessStarter):
            timeout = 10
            pattern = "started"
            args = [
                sys.executable,
                curdir / "simulated_server/initialize_server.py",
                port,
            ]

        xprocess.ensure("server-%s" % port, Starter)
        yield port
        xprocess.getinfo("server-%s" % port).terminate()
    else:
        yield port
        return


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

        if request.config.getoption("--engineering"):
            c.set_engineering_mode(
                enable=True, password=request.config.getoption("--engineering")
            )
        yield c
        time.sleep(4)
        c.disconnect()
        return
    else:
        port = np.random.randint(5000, 9999)
        curdir = pathlib.Path(__file__).parent.parent

        class Starter(ProcessStarter):
            timeout = 50
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
