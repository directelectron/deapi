"""Zero-copy CuPy access to DE-Server's GPU movie buffers (Windows, same computer).

    with client.get_gpu_frames() as frames:   # before start_acquisition: maps both buffers
        client.start_acquisition(1)
        for batch in frames:                  # one finished movie buffer
            batch.images                      # cupy float32 (images, height, width), server memory
            batch.info                        # numpy view: frame, scanX, scanY, valid per image
        # the buffer goes back to the server when the loop advances

The server processes into two ping-pong movie buffers; while this process holds one, the
server's processing waits for it, so finish (or copy) what you need inside the loop body.
GPU work queued on the current stream of the buffers' GPU (and of each of `peer_devices`)
is synchronized before the release; synchronize work on other streams yourself.

DEAPI hands this process a handle to a small control block once. The server duplicates the
buffer and semaphore handles into this process itself and lists them there, again whenever
it reallocates the buffers or starts a new acquisition while a buffer is held, so no DEAPI
round trip is needed during an acquisition.

More than one GPU: `frames.device` is the GPU that holds the buffers, in this process's
numbering (read from the memory itself, so CUDA_VISIBLE_DEVICES cannot mislead it). Pass
other GPUs as `peer_devices`: where the driver allows peer access the buffers are mapped
for them too, so their kernels read server memory directly (`frames.peer_access`);
otherwise `with cp.cuda.Device(d): cp.asarray(batch.images)` copies. Either way their
current streams are synchronized before each release.

More than one computer: only a process on the server computer can map the buffers (the
server refuses others). Run a bridge there that iterates these frames and sends each batch
on (GPUDirect RDMA, NCCL, or pinned host memory and a socket) before releasing it; the
receiving side can present the same FrameSource interface to its consumers.
"""

import ctypes
import threading
import time
import warnings
from ctypes import c_int, c_size_t, c_uint64 as u64, c_void_p, wintypes

import numpy as np

VERSION, BUFFERS, MAX_IMAGES = 4, 2, 1024  # must match GpuFrameSharing/Protocol.h
H = wintypes.HANDLE
WAIT_OBJECT_0, WAIT_TIMEOUT, WAIT_FAILED = 0, 0x102, 0xFFFFFFFF
IMAGE = np.dtype(
    [
        ("frame", "<i8"),
        ("scanX", "<i4"),
        ("scanY", "<i4"),
        ("valid", "<i4"),
        ("pad", "<i4"),
    ]
)
PROFILE = (
    "produced",
    "released",
    "unshared",
    "holdNs",
    "holdMaxNs",
    "setupNs",
    "publishNs",
    "publishMaxNs",
)


class _Slot(ctypes.Structure):
    _fields_ = [
        (n, u64)
        for n in (
            "buffer",
            "count",
            "width",
            "height",
            "rowBytes",
            "imageBytes",
            "publishedNs",
        )
    ] + [("image", ctypes.c_byte * (IMAGE.itemsize * MAX_IMAGES))]


class _ClientHandles(ctypes.Structure):
    _fields_ = [
        ("filled", u64),
        ("free", u64 * BUFFERS),
        ("buffer", u64 * BUFFERS),
        ("detach", u64),
        ("session", u64),
    ]


class _Control(ctypes.Structure):
    _fields_ = (
        [
            ("version", ctypes.c_uint32),
            ("device", ctypes.c_uint32),
            ("bufferBytes", u64),
            ("client", _ClientHandles),
        ]
        + [(n, u64) for n in PROFILE]
        + [("slot", _Slot * BUFFERS)]
    )


class _Location(ctypes.Structure):  # CUmemLocation
    _fields_ = [("type", c_int), ("id", c_int)]


class _AllocationProp(ctypes.Structure):  # CUmemAllocationProp
    _fields_ = [
        ("type", c_int),
        ("requestedHandleTypes", c_int),
        ("location", _Location),
        ("win32HandleMetaData", c_void_p),
        ("allocFlags", ctypes.c_ubyte * 8),
    ]


class _AccessDesc(ctypes.Structure):  # CUmemAccessDesc
    _fields_ = [("location", _Location), ("flags", c_int)]


_LOCATION_DEVICE, _ACCESS_READWRITE, _HANDLE_WIN32 = 1, 3, 2
_k32 = _cu = None


def _load_dlls():
    """kernel32 and the CUDA driver, loaded on first use so this module imports anywhere
    (the simulated path below needs neither)."""
    global _k32, _cu
    if _k32 is not None:
        return
    k32, cu = ctypes.WinDLL("kernel32", use_last_error=True), ctypes.WinDLL("nvcuda")
    DWORD, BOOL = wintypes.DWORD, wintypes.BOOL
    for name, restype, argtypes in [
        ("MapViewOfFile", c_void_p, [H, DWORD, DWORD, DWORD, c_size_t]),
        ("UnmapViewOfFile", BOOL, [c_void_p]),
        ("WaitForSingleObject", DWORD, [H, DWORD]),
        ("ReleaseSemaphore", BOOL, [H, wintypes.LONG, c_void_p]),
        ("SetEvent", BOOL, [H]),
        ("CloseHandle", BOOL, [H]),
    ]:
        getattr(k32, name).restype, getattr(k32, name).argtypes = restype, argtypes
    P = ctypes.POINTER
    for name, argtypes in [
        ("cuInit", [ctypes.c_uint]),
        ("cuGetErrorName", [c_int, P(ctypes.c_char_p)]),
        ("cuMemImportFromShareableHandle", [P(u64), c_void_p, c_int]),
        ("cuMemGetAllocationPropertiesFromHandle", [P(_AllocationProp), u64]),
        ("cuMemAddressReserve", [P(u64), c_size_t, c_size_t, u64, u64]),
        ("cuMemMap", [u64, c_size_t, c_size_t, u64, u64]),
        ("cuMemSetAccess", [u64, c_size_t, P(_AccessDesc), c_size_t]),
        ("cuMemUnmap", [u64, c_size_t]),
        ("cuMemAddressFree", [u64, c_size_t]),
        ("cuMemRelease", [u64]),
        ("cuDeviceCanAccessPeer", [P(c_int), c_int, c_int]),
    ]:
        getattr(cu, name).restype, getattr(cu, name).argtypes = c_int, argtypes
    _check(cu.cuInit(0), cu)
    _k32, _cu = k32, cu


def _check(result, cu=None):
    if result:
        name = ctypes.c_char_p()
        (cu or _cu).cuGetErrorName(result, ctypes.byref(name))
        raise RuntimeError(
            f"CUDA driver error {result} ({(name.value or b'?').decode()})"
        )


#: What deapi's simulated server answers GET_GPU_FRAMES with.
SIMULATED = "simulated"


def open_gpu_frames(values, client, peer_devices=()):
    """The frames for what the server answered GET_GPU_FRAMES with: a GpuFrames over the
    control block handle it sent, or a SimulatedGpuFrames for the simulated server.
    `client` reads properties (`client[name]`) and `client.acquiring`."""
    if values and values[0] == SIMULATED:
        return SimulatedGpuFrames(client)
    return GpuFrames(lambda: [int(values[0])], peer_devices=peer_devices)


class Batch:
    """One finished movie buffer: `images` and `info`, valid until released (the loop
    advances). `images` lives on GPU `device` (None: NumPy, no GPU)."""

    def __init__(self, images, info, device=None):
        self.images, self.info, self.device = images, info, device


class FrameSource:
    """What get_gpu_frames returns: iterate it (or `batches(idle_s)`) for Batches, and close
    it when done (or use it as a context manager). A source that forwards batches from
    another computer implements the same interface."""

    device = None

    def batches(self, idle_s=None):
        """Yield each Batch; with `idle_s`, also yield None after that long without one,
        so the caller can check whether to stop."""
        raise NotImplementedError

    def __iter__(self):
        return self.batches()

    def server_profile(self):
        return {}

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class GpuFrames(FrameSource):
    """The server's two GPU movie buffers mapped into this process, plus the semaphores.

    `attach()` must return [control block handle] from DE-Server (Client.get_gpu_frames
    does this over DEAPI). Call close() when done: while this process holds a published
    buffer, the server's processing waits for it. Iterate from one thread at a time (any
    thread); close() may come from another thread, and then first waits for the batch that
    thread holds to be released.
    """

    def __init__(self, attach, peer_devices=()):
        import cupy as cp

        _load_dlls()
        self._cp, self._peers = cp, tuple(int(d) for d in peer_devices)
        count = cp.cuda.runtime.getDeviceCount()
        for device in self._peers:
            if not 0 <= device < count:
                raise ValueError(
                    f"peer device {device} does not exist: this process sees {count} GPU(s)"
                )
        self._lock = threading.Condition()
        self._closed, self._holder, self._warned = False, None, False
        self.session, self.device, self.peer_access, self.size = 0, None, {}, 0
        self._pointers, self._filled, self._free, self._detach = [], None, [], None
        self.buffers, self._views, self._control = [], {}, None
        # This process, in ns: CuPy context creation and mapping (setup), and per buffer the
        # pickup (server publish -> picked up here, including queueing), wrap and sync times.
        self.profile = dict(
            contextNs=0,
            attachNs=0,
            buffers=0,
            pickupNs=0,
            pickupMaxNs=0,
            wrapNs=0,
            wrapMaxNs=0,
            syncNs=0,
            syncMaxNs=0,
        )
        (self._control_handle,) = attach()
        address = _k32.MapViewOfFile(
            H(self._control_handle), 0xF001F, 0, 0, ctypes.sizeof(_Control)
        )  # all access
        if not address:
            error = ctypes.WinError(ctypes.get_last_error())
            _k32.CloseHandle(H(self._control_handle))
            raise error
        self._control = _Control.from_address(address)
        try:
            if self._control.version != VERSION:
                raise RuntimeError(
                    f"DE-Server GPU frame protocol {self._control.version}, this client expects {VERSION}"
                )
            self._unshared = self._control.unshared
            self._load()
        except BaseException:
            self._closed = True
            self._unload()
            self._release_control()
            raise

    def _count(self, name, ns):
        self.profile[name + "Ns"] += ns
        self.profile[name + "MaxNs"] = max(self.profile[name + "MaxNs"], ns)

    def _load(self):
        """Take the buffer and semaphore handles the server listed (again when they change).
        Called with the lock held, or from __init__."""
        listed, deadline = self._control.client, time.monotonic() + 10
        while True:  # 0 while the server updates the list
            session = listed.session
            filled, free, buffers, detach = (
                listed.filled,
                list(listed.free),
                list(listed.buffer),
                listed.detach,
            )
            if session and listed.session == session:
                break
            if time.monotonic() > deadline:
                raise TimeoutError(
                    "DE-Server did not finish listing its GPU frame handles"
                )
            time.sleep(0.001)
        start = time.perf_counter_ns()
        self._unload()
        self._filled, self._free, self._detach = filled, free, detach
        self.session, self.size = session, self._control.bufferBytes
        allocations = []
        try:
            for (
                handle
            ) in buffers:  # import, which leaves the duplicated handle to close
                allocation = u64()
                result = _cu.cuMemImportFromShareableHandle(
                    ctypes.byref(allocation), handle, _HANDLE_WIN32
                )
                _k32.CloseHandle(H(handle))
                _check(result)
                allocations.append(allocation)
            devices = set()  # the GPU holding the memory, in this process's numbering
            for allocation in allocations:
                prop = _AllocationProp()
                _check(
                    _cu.cuMemGetAllocationPropertiesFromHandle(
                        ctypes.byref(prop), allocation
                    )
                )
                devices.add(prop.location.id)
            if len(devices) != 1:
                raise RuntimeError(f"GPU movie buffers on several GPUs: {devices}")
            self.device = devices.pop()
            context = time.perf_counter_ns()
            for device in (
                *self._peers,
                self.device,
            ):  # contexts now, not mid-acquisition
                with self._cp.cuda.Device(device):
                    self._cp.cuda.runtime.free(0)
            context = time.perf_counter_ns() - context
            self.profile["contextNs"] += context
            with self._cp.cuda.Device(self.device):
                self.peer_access = {d: self._can_access(d) for d in self._peers}
                access = [self.device] + [
                    d for d, ok in self.peer_access.items() if ok and d != self.device
                ]
                for allocation in allocations:
                    self._pointers.append(self._map(allocation, access))
        finally:
            for allocation in allocations:
                _cu.cuMemRelease(allocation)  # a mapping keeps the memory alive
        # Both movie buffers, flat; batches are views into these.
        self.buffers = [
            self._cp.ndarray(
                (self.size // 4,),
                self._cp.float32,
                self._cp.cuda.MemoryPointer(
                    self._cp.cuda.UnownedMemory(p, self.size, self, self.device), 0
                ),
            )
            for p in self._pointers
        ]
        self._views, self._consumed = {}, 0
        self.profile["attachNs"] += time.perf_counter_ns() - start - context

    def _can_access(self, device):
        """Whether `device`'s kernels can read memory on the buffers' GPU directly."""
        if device == self.device:
            return True
        can = c_int()
        _check(_cu.cuDeviceCanAccessPeer(ctypes.byref(can), device, self.device))
        return bool(can.value)

    def _map(self, allocation, devices):
        """Map one imported buffer for `devices` (CUDA VMM); no data is copied."""
        pointer, size = u64(), self.size
        _check(_cu.cuMemAddressReserve(ctypes.byref(pointer), size, 0, 0, 0))
        try:
            _check(_cu.cuMemMap(pointer, size, 0, allocation, 0))
            access = (_AccessDesc * len(devices))(
                *(
                    _AccessDesc(_Location(_LOCATION_DEVICE, d), _ACCESS_READWRITE)
                    for d in devices
                )
            )
            result = _cu.cuMemSetAccess(pointer, size, access, len(devices))
            if result:
                _cu.cuMemUnmap(pointer, size)
                _check(result)
        except BaseException:
            _cu.cuMemAddressFree(pointer, size)
            raise
        return pointer.value

    def _unload(self):
        """Unmap the buffers and close the semaphore handles (lock held)."""
        if self._pointers:
            with self._cp.cuda.Device(self.device):
                self._cp.cuda.Device(self.device).synchronize()
                self.buffers, self._views = [], {}
                for pointer in self._pointers:
                    _cu.cuMemUnmap(pointer, self.size)
                    _cu.cuMemAddressFree(pointer, self.size)
        self._pointers, self.buffers, self._views = [], [], {}
        for handle in (self._filled, *self._free, self._detach):
            if handle:
                _k32.CloseHandle(H(handle))
        self._filled, self._free, self._detach = None, [], None

    def server_profile(self):
        """The server's counters (see PROFILE; times in ns)."""
        with self._lock:
            if self._control is None:
                return {}
            return {name: getattr(self._control, name) for name in PROFILE}

    def _check_unshared(self):
        """Warn once if the server finished buffers it could not share while attached."""
        if not self._warned and self._control.unshared != self._unshared:
            self._warned = True
            warnings.warn(
                "DE-Server finished movie buffers it could not share with this process "
                f"(more than {MAX_IMAGES} images per buffer, or an event-counting mode "
                "without movie images); see server_profile()['unshared']",
                RuntimeWarning,
                stacklevel=3,
            )

    def batches(self, idle_s=None):
        """Yield each finished buffer as a Batch; with `idle_s`, also yield None after that
        long without one, so the caller can check whether to stop."""
        cp, waited = self._cp, 0.0
        while True:
            with self._lock:
                if self._closed:
                    return
                if self._control.client.session != self.session:  # new handles listed
                    self._load()
                result = _k32.WaitForSingleObject(H(self._filled), 100)
                if result == WAIT_FAILED:
                    raise ctypes.WinError(ctypes.get_last_error())
                if result == WAIT_OBJECT_0:
                    woke = time.perf_counter_ns()
                    if self._control.client.session != self.session:
                        # A count left from a session the server has since replaced: the
                        # slots now describe the new session's buffers, not one we hold.
                        self._load()
                        continue
                    session = self.session
                    slot = self._control.slot[self._consumed % BUFFERS]
                    buffer = slot.buffer
                    key = (buffer, slot.count, slot.width, slot.height)
                    if key not in self._views:  # arrays over fixed offsets, built once
                        self._views[key] = cp.ndarray(
                            (slot.count, slot.height, slot.width),
                            cp.float32,
                            self.buffers[buffer].data,
                            strides=(slot.imageBytes, slot.rowBytes, 4),
                        )
                    info = np.frombuffer(slot.image, IMAGE, slot.count)  # slot view
                    batch = Batch(self._views[key], info, self.device)
                    free, self._holder = self._free[buffer], threading.get_ident()
                    self._consumed += 1
                    self._count("pickup", woke - slot.publishedNs)
                    self._count("wrap", time.perf_counter_ns() - woke)
                self._check_unshared()
            if result != WAIT_OBJECT_0:  # nothing yet
                waited += 0.1
                if idle_s is not None and waited >= idle_s:
                    waited = 0.0
                    yield None
                continue
            waited = 0.0
            try:
                yield batch
            finally:
                del batch
                self._release(free, session)

    def _release(self, free, session):
        """Give a buffer back once the GPU work queued on it is done."""
        synced = time.perf_counter_ns()
        try:
            for device in (self.device, *self._peers):
                with self._cp.cuda.Device(device):
                    self._cp.cuda.get_current_stream().synchronize()
        finally:
            with self._lock:
                # After close() or a new session the server took the buffer back itself,
                # and the handle may be closed already: releasing it is no longer ours.
                if not self._closed and session == self.session:
                    _k32.ReleaseSemaphore(H(free), 1, None)
                self._holder = None
                self._lock.notify_all()
            self._count("sync", time.perf_counter_ns() - synced)
            self.profile["buffers"] += 1

    def close(self):
        """Stop sharing: the server gets any held buffer back and stops waiting (no DEAPI
        call). Safe to call more than once, and from another thread."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            me = threading.get_ident()
            # Another thread still working on a batch: let it finish before unmapping.
            self._lock.wait_for(lambda: self._holder in (None, me))
            if self._detach:
                _k32.SetEvent(H(self._detach))
            self._unload()
            self._release_control()

    def _release_control(self):
        if self._control is not None:
            _k32.UnmapViewOfFile(ctypes.addressof(self._control))
            _k32.CloseHandle(H(self._control_handle))
            self._control = None


class SimulatedGpuFrames(FrameSource):
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
        self.device, self.session, self.peer_access = None, 1, {}
        self.profile = dict(buffers=0)

    def batches(self, idle_s=None):
        """As GpuFrames.batches: each batch, and None every `idle_s` seconds without one."""
        from deapi.fake_data.grains import TiltGrains
        from deapi.simulated_server.fake_server import SIMULATED_MAX_FPS

        c, waited = self._client, 0.0
        while c.acquisitions_started == self._after:  # wait for the acquisition
            if self._closed:
                return
            time.sleep(0.05)
            waited += 0.05
            if idle_s is not None and waited >= idle_s:
                waited = 0.0
                yield None
        scanning = c["Scan - Enable"] == "On"
        sx, sy = (
            (int(c["Scan - Size X"]), int(c["Scan - Size Y"])) if scanning else (1, 1)
        )
        points = sx * sy
        total = points * (int(c["Scan - Repeats"] or 1) if scanning else 1)
        k = int(c["Sensor Size X (pixels)"])
        fps = min(float(c["Frames Per Second"]), SIMULATED_MAX_FPS)
        data = TiltGrains(x_pixels=sx, y_pixels=sy, kx_pixels=k, ky_pixels=k)
        signal = np.asarray(data._signal, dtype=np.float32)
        start, done, checked, waited = c.acquisition_started_at, 0, 0.0, 0.0
        while done < total and not self._closed:
            now = time.monotonic()
            if now - checked > 0.1:  # one round trip per 100 ms
                checked = now
                if not c.acquiring and now < start + total / fps - 0.5:
                    return  # stopped early
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
