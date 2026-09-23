"""get_gpu_frames against the simulated server: the same interface as the real, zero-copy
GpuFrames, with NumPy batches of the simulated dataset."""

import time

import numpy as np
import pytest

from deapi.gpu_frames import SimulatedGpuFrames


@pytest.fixture(autouse=True)
def _restore(client):
    """The client is shared by the whole session: leave the scan as it was found."""
    before = {name: client[name] for name in ("Scan - Enable", "Scan - Size X", "Scan - Size Y",
                                              "Scan - Repeats", "Frames Per Second")}
    yield
    for name, value in before.items():
        client[name] = value


def _scan(client, size, repeats):
    client["Scan - Enable"] = "On"
    client["Scan - Size X"] = size
    client["Scan - Size Y"] = size
    client["Scan - Repeats"] = repeats
    client["Frames Per Second"] = 1000


def test_simulated_frames_cover_every_scan_position(client):
    _scan(client, 8, 2)
    frames = client.get_gpu_frames()
    assert isinstance(frames, SimulatedGpuFrames)
    client.start_acquisition(1)
    seen, positions, deadline = 0, set(), time.monotonic() + 30
    for batch in frames.batches(idle_s=0.2):
        assert time.monotonic() < deadline
        if batch is None:
            continue
        assert batch.images.dtype == np.float32 and batch.images.ndim == 3
        assert batch.info["valid"].all()
        seen += len(batch.images)
        positions.update(zip(batch.info["scanX"].tolist(), batch.info["scanY"].tolist()))
    frames.close()
    assert seen == 8 * 8 * 2
    assert positions == {(x, y) for x in range(8) for y in range(8)}


def test_stop_ends_the_simulated_frames(client):
    _scan(client, 8, 1000)
    frames = client.get_gpu_frames()
    client.start_acquisition(1)
    seen, started, deadline = 0, time.monotonic(), time.monotonic() + 30
    for batch in frames.batches(idle_s=0.2):
        assert time.monotonic() < deadline
        if batch is not None:
            seen += len(batch.images)
        if seen and time.monotonic() - started > 0.5 and client.acquiring:
            assert client.stop_acquisition()
    frames.close()
    assert 0 < seen < 8 * 8 * 1000
    assert not client.acquiring
