import sys, socket, pytest, py, pathlib
from xprocess import ProcessStarter
from deapi.client import Client

import time
import numpy as np


@pytest.fixture(scope="module")
def client(xprocess):
    port = np.random.randint(5000, 9999)
    curdir = pathlib.Path(__file__).parent.parent

    class Starter(ProcessStarter):
        timeout = 20
        pattern = "started"
        args = [sys.executable, curdir / "simulated_server/initialize_server.py", port]

    xprocess.ensure("server-%s" % port, Starter)
    c = Client()
    c.usingMmf = False
    c.connect(port=port)
    yield c
    xprocess.getinfo("server-%s" % port).terminate()
