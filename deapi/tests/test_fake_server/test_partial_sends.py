"""The client must deliver every byte even when ``socket.send`` sends only part of a buffer.

``send`` is allowed to accept fewer bytes than it was given, and does so whenever the
socket has a timeout and the kernel's send buffer fills up -- routinely on macOS's
loopback. Dropping the rest of a buffer leaves the server waiting for bytes that never
come, and every later command on that connection hangs.
"""

import pathlib
import socket
import sys
import threading

import numpy as np
import pytest
from xprocess import ProcessStarter

from deapi import Client


class _TrickleSocket:
    """A socket whose ``send`` accepts at most ``limit`` bytes per call."""

    def __init__(self, sock, limit=1000):
        self._sock = sock
        self._limit = limit

    def send(self, data, *args):
        return self._sock.send(bytes(data[: self._limit]), *args)

    def sendall(self, data, *args):
        view = memoryview(data)
        while len(view):
            view = view[self.send(view) :]

    def __getattr__(self, name):
        return getattr(self._sock, name)


@pytest.fixture
def trickle_client(xprocess):
    # its own simulated server: a hung connection must not leak into other tests
    port = int(np.random.randint(10000, 12000))
    script = pathlib.Path(__file__).parents[2] / "simulated_server/initialize_server.py"

    class Starter(ProcessStarter):
        timeout = 60
        pattern = "started"
        args = [sys.executable, "-u", script, port]

    xprocess.ensure(f"trickle-server-{port}", Starter)
    c = Client()
    c.usingMmf = False
    c.connect(port=port)
    c.socket = _TrickleSocket(c.socket)
    yield c
    try:
        c.disconnect()
    finally:
        xprocess.getinfo(f"trickle-server-{port}").terminate()


@pytest.mark.timeout(30)
def test_virtual_mask_survives_partial_sends(trickle_client):
    trickle_client.virtual_masks[2][:] = 2
    np.testing.assert_allclose(trickle_client.virtual_masks[2][:], 2)
    # the connection is still in step: the next command gets its own answer
    assert trickle_client["Scan - Enable"] in ("On", "Off")


@pytest.mark.timeout(30)
def test_send_helper_delivers_every_byte():
    """The helper behind virtual masks and XY scan arrays, without a server."""
    a, b = socket.socketpair()
    try:
        c = Client()
        c.socket = _TrickleSocket(a, limit=777)
        payload = np.arange(300_000, dtype=np.uint32).tobytes()
        received = bytearray()

        def read():
            while len(received) < len(payload):
                received.extend(b.recv(65536))

        reader = threading.Thread(target=read)
        reader.start()
        c._Client__sendToSocket(c.socket, payload, len(payload))
        reader.join(10)
        assert bytes(received) == payload
    finally:
        a.close()
        b.close()
