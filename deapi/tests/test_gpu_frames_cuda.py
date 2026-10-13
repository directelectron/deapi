"""GpuFrames checks that need CuPy and a GPU but no DE-Server."""

import pytest

cp = pytest.importorskip("cupy")
try:
    if cp.cuda.runtime.getDeviceCount() < 1:
        pytest.skip("no GPU", allow_module_level=True)
except cp.cuda.runtime.CUDARuntimeError:
    pytest.skip("no CUDA driver", allow_module_level=True)

from deapi.gpu_frames import GpuFrames


def test_missing_peer_device_fails_before_attaching():
    count = cp.cuda.runtime.getDeviceCount()
    with pytest.raises(ValueError, match=f"sees {count} GPU"):
        GpuFrames(lambda: pytest.fail("attached"), peer_devices=[count])
