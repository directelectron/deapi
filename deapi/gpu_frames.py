"""Zero-copy CuPy access to DE-Server's GPU movie buffers (Windows, same computer).

    frames = client.get_gpu_frames()      # before start_acquisition: maps both buffers
    client.start_acquisition(1)
    for batch in frames:                  # one finished movie buffer
        batch.images                      # cupy float32 (images, height, width), server memory
        batch.info                        # numpy view: frame, scanX, scanY, valid per image
    # the buffer goes back to the server when the loop advances

The server processes into two ping-pong movie buffers; while this process holds one, the
server's processing waits for it, so finish (or copy) what you need inside the loop body.
GPU work queued on CuPy's current stream is synchronized before the release; synchronize
work on other streams yourself.

DEAPI hands this process a handle to a small control block once. The server duplicates the
buffer and semaphore handles into this process itself and lists them there, again whenever
it reallocates the buffers, so no DEAPI round trip is needed during an acquisition.
"""
import ctypes
import time
from ctypes import c_size_t, c_uint64 as u64, wintypes

import numpy as np

VERSION, BUFFERS, MAX_IMAGES = 4, 2, 1024     # must match GpuFrameSharing/Protocol.h
H = wintypes.HANDLE
IMAGE = np.dtype([("frame", "<i8"), ("scanX", "<i4"), ("scanY", "<i4"), ("valid", "<i4"), ("pad", "<i4")])
PROFILE = ("produced", "released", "unshared", "holdNs", "holdMaxNs", "setupNs", "publishNs", "publishMaxNs")


class _Slot(ctypes.Structure):
    _fields_ = [(n, u64) for n in ("buffer", "count", "width", "height", "rowBytes", "imageBytes", "publishedNs")] + [
        ("image", ctypes.c_byte * (IMAGE.itemsize * MAX_IMAGES))]


class _ClientHandles(ctypes.Structure):
    _fields_ = [("filled", u64), ("free", u64 * BUFFERS), ("buffer", u64 * BUFFERS), ("detach", u64), ("session", u64)]


class _Control(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint32), ("device", ctypes.c_uint32), ("bufferBytes", u64),
                ("client", _ClientHandles)] + [(n, u64) for n in PROFILE] + [("slot", _Slot * BUFFERS)]


_k32 = _cu = None


def _load_dlls():
    """kernel32 and the CUDA driver, loaded on first use so this module imports anywhere
    (the simulated path below needs neither)."""
    global _k32, _cu
    if _k32 is None:
        _k32, _cu = ctypes.WinDLL("kernel32"), ctypes.WinDLL("nvcuda")
        _k32.MapViewOfFile.restype = ctypes.c_void_p
        _k32.MapViewOfFile.argtypes = [H, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, c_size_t]
        _k32.SetEvent.argtypes = [H]


#: What deapi's simulated server answers GET_GPU_FRAMES with.
SIMULATED = "simulated"


def open_gpu_frames(values, client):
    """The frames for what the server answered GET_GPU_FRAMES with: a GpuFrames over the
    control block handle it sent, or a SimulatedGpuFrames for the simulated server.
    `client` reads properties (`client[name]`) and `client.acquiring`."""
    if values and values[0] == SIMULATED:
        return SimulatedGpuFrames(client)
    return GpuFrames(lambda: [int(values[0])])


def _check(result):
    if result:
        raise RuntimeError(f"CUDA driver error {result}")


class Batch:
    """One finished movie buffer: `images` (cupy) and `info` (numpy), valid until released."""

    def __init__(self, images, info):
        self.images, self.info = images, info


class GpuFrames:
    """The server's two GPU movie buffers mapped into this process, plus the semaphores.

    `attach()` must return [control block handle] from DE-Server (DeClient.get_gpu_frames
    does this over DEAPI). Call close() when done, or keep iterating: while this process
    holds a published buffer, the server's processing waits for it.
    """

    def __init__(self, attach):
        import cupy as cp
        _load_dlls()
        self._cp, self._attach, self.session, self._pointers = cp, attach, 0, []
        # This process, in ns: CuPy context creation and mapping (setup), and per buffer the
        # pickup (server publish -> picked up here, including queueing), wrap and sync times.
        self.profile = dict(contextNs=0, attachNs=0, buffers=0, pickupNs=0, pickupMaxNs=0,
                            wrapNs=0, wrapMaxNs=0, syncNs=0, syncMaxNs=0)
        (self._control_handle,) = attach()
        address = _k32.MapViewOfFile(H(self._control_handle), 0xF001F, 0, 0, ctypes.sizeof(_Control))  # all access
        if not address:
            raise ctypes.WinError()
        self._control = _Control.from_address(address)
        if self._control.version != VERSION:
            raise RuntimeError(f"DE-Server GPU frame protocol {self._control.version}, this client expects {VERSION}")
        self.device = self._control.device
        start = time.perf_counter_ns()
        cp.cuda.Device(self.device).use()
        cp.cuda.runtime.free(0)                          # create CuPy's CUDA context for the driver calls
        self.profile["contextNs"] += time.perf_counter_ns() - start
        self._load()

    def _count(self, name, ns):
        self.profile[name + "Ns"] += ns
        self.profile[name + "MaxNs"] = max(self.profile[name + "MaxNs"], ns)

    def _load(self):
        """Take the buffer and semaphore handles the server listed (again when they change)."""
        cp, listed = self._cp, self._control.client
        while True:                                      # 0 while the server updates the list
            session = listed.session
            filled, free, buffers, detach = listed.filled, list(listed.free), list(listed.buffer), listed.detach
            if session and listed.session == session:
                break
            time.sleep(0.001)
        start = time.perf_counter_ns()
        self._unload()
        self.size = self._control.bufferBytes
        self.filled, self.free, self._detach = filled, free, detach
        self._pointers = [self._map(handle) for handle in buffers]
        # Both movie buffers, flat, before any acquisition; batches are views into these.
        self.buffers = [cp.ndarray((self.size // 4,), cp.float32,
                                   cp.cuda.MemoryPointer(cp.cuda.UnownedMemory(p, self.size, self, self.device), 0))
                        for p in self._pointers]
        self._views, self._consumed, self.session = {}, 0, session
        self.profile["attachNs"] += time.perf_counter_ns() - start

    def _map(self, handle):
        """Map one server buffer into this process (CUDA VMM import); no data is copied."""
        allocation, pointer, size = u64(), u64(), c_size_t(self.size)
        _check(_cu.cuMemImportFromShareableHandle(ctypes.byref(allocation), H(handle), 2))  # Win32 handle
        _k32.CloseHandle(H(handle))
        _check(_cu.cuMemAddressReserve(ctypes.byref(pointer), size, c_size_t(0), u64(0), u64(0)))
        _check(_cu.cuMemMap(pointer, size, c_size_t(0), allocation, u64(0)))
        _check(_cu.cuMemSetAccess(pointer, size, (ctypes.c_int * 3)(1, self.device, 3), c_size_t(1)))  # read/write
        _cu.cuMemRelease(allocation)                     # the mapping keeps the memory alive
        return pointer.value

    def _unload(self):
        if not self._pointers:
            return
        self._cp.cuda.Device(self.device).synchronize()
        self.buffers, self._views = [], {}
        for pointer in self._pointers:
            _cu.cuMemUnmap(u64(pointer), c_size_t(self.size))
            _cu.cuMemAddressFree(u64(pointer), c_size_t(self.size))
        for handle in (self.filled, *self.free, self._detach):
            _k32.CloseHandle(H(handle))
        self._pointers = []

    def server_profile(self):
        """The server's counters (see PROFILE; times in ns)."""
        return {name: getattr(self._control, name) for name in PROFILE}

    def __iter__(self):
        return self.batches()

    def batches(self, idle_s=None):
        """Yield each finished buffer as a Batch; with `idle_s`, also yield None after that
        long without one, so the caller can check whether to stop."""
        cp, waited = self._cp, 0.0
        while True:
            if _k32.WaitForSingleObject(H(self.filled), 100):   # nothing yet
                if self._control.client.session != self.session:  # server reallocated / restarted
                    self._load()
                waited += 0.1
                if idle_s is not None and waited >= idle_s:
                    waited = 0.0
                    yield None
                continue
            waited = 0.0
            woke = time.perf_counter_ns()
            slot = self._control.slot[self._consumed % BUFFERS]
            buffer = slot.buffer
            key = (buffer, slot.count, slot.width, slot.height)
            if key not in self._views:                          # arrays over fixed offsets, built once
                self._views[key] = cp.ndarray((slot.count, slot.height, slot.width), cp.float32,
                                              self.buffers[buffer].data, strides=(slot.imageBytes, slot.rowBytes, 4))
            info = np.frombuffer(slot.image, IMAGE, slot.count)  # view of the shared slot
            self._count("pickup", woke - slot.publishedNs)
            self._count("wrap", time.perf_counter_ns() - woke)
            try:
                yield Batch(self._views[key], info)
            finally:
                synced = time.perf_counter_ns()
                cp.cuda.get_current_stream().synchronize()     # work queued on the images is done
                self._count("sync", time.perf_counter_ns() - synced)
                self.profile["buffers"] += 1
                self._consumed += 1
                _k32.ReleaseSemaphore(H(self.free[buffer]), 1, None)

    def close(self):
        """Stop sharing: the server gets any held buffer back and stops waiting (no DEAPI call)."""
        _k32.SetEvent(H(self._detach))
        self._unload()
        _k32.UnmapViewOfFile(ctypes.c_void_p(ctypes.addressof(self._control)))
        _k32.CloseHandle(H(self._control_handle))


class SimulatedGpuFrames:
    """GpuFrames' interface over deapi's simulated server, for clients developed offline.

    Batches are NumPy float32 frames of the server's own simulated dataset (the TiltGrains
    its results come from), built in this process and delivered at the server's frame rate
    while it acquires. These are copies and there is no GPU: a stand-in for testing, not
    the zero-copy path. `client` reads properties (`client[name]`) and `client.acquiring`,
    and carries the Client's `acquisitions_started` / `acquisition_started_at`: the frames
    belong to the next acquisition started after this was made, timed from its start.
    """

    BATCH = 32

    def __init__(self, client):
        self._client, self._closed = client, False
        self._after = client.acquisitions_started
        self.device, self.session = None, 1
        self.profile = dict(buffers=0)

    def server_profile(self):
        return {}

    def __iter__(self):
        return self.batches()

    def batches(self, idle_s=None):
        """As GpuFrames.batches: each batch, and None every `idle_s` seconds without one."""
        from deapi.fake_data.grains import TiltGrains
        from deapi.simulated_server.fake_server import SIMULATED_MAX_FPS

        c, waited = self._client, 0.0
        while c.acquisitions_started == self._after:      # wait for the acquisition
            if self._closed:
                return
            time.sleep(0.05)
            waited += 0.05
            if idle_s is not None and waited >= idle_s:
                waited = 0.0
                yield None
        scanning = c["Scan - Enable"] == "On"
        sx, sy = (int(c["Scan - Size X"]), int(c["Scan - Size Y"])) if scanning else (1, 1)
        points = sx * sy
        total = points * (int(c["Scan - Repeats"] or 1) if scanning else 1)
        k = int(c["Sensor Size X (pixels)"])
        fps = min(float(c["Frames Per Second"]), SIMULATED_MAX_FPS)
        data = TiltGrains(x_pixels=sx, y_pixels=sy, kx_pixels=k, ky_pixels=k)
        signal = np.asarray(data._signal, dtype=np.float32)
        start, done, checked, waited = c.acquisition_started_at, 0, 0.0, 0.0
        while done < total and not self._closed:
            now = time.monotonic()
            if now - checked > 0.1:                       # one round trip per 100 ms
                checked = now
                if not c.acquiring and now < start + total / fps - 0.5:
                    return                                # stopped early
            due = min(total, int((now - start) * fps))
            if due <= done:
                time.sleep(0.005)
                waited += 0.005
                if idle_s is not None and waited >= idle_s:
                    waited = 0.0
                    yield None
                continue
            n = min(self.BATCH, due - done)
            frame = np.arange(done, done + n)
            x, y = frame % points % sx, frame % points // sx
            info = np.zeros(n, IMAGE)
            info["frame"], info["scanX"], info["scanY"], info["valid"] = frame, x, y, 1
            yield Batch(signal[data.navigator[x, y]], info)
            self.profile["buffers"] += 1
            done += n
            waited = 0.0

    def close(self):
        self._closed = True
