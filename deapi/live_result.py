"""LiveResult: continuously-updating anyplotlib display for DE camera frames."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import numpy as np

from deapi.data_types import Histogram

if TYPE_CHECKING:
    from deapi.client import Client
    from deapi.data_types import Attributes, Result

_IDLE_SLEEP = 0.5  # 2 Hz idle poll for client.acquiring


class LiveResult:
    """Continuously streams frames from the DE server into an anyplotlib widget.

    Create via :meth:`deapi.Client.live_result` rather than instantiating
    directly.

    Parameters
    ----------
    client : deapi.Client
        Connected DE client.
    frame_type : str
        Frame type accepted by :meth:`~deapi.Client.get_result`,
        e.g. ``"singleframe_integrated"``, ``"virtual_image0"``.
    display_fps : float
        Target display refresh rate in frames per second. Default 30.
    window_width : int, optional
        Server-side resize width in pixels. ``None`` means full width.
    window_height : int, optional
        Server-side resize height in pixels. ``None`` means full height.

    Attributes
    ----------
    result : Result or None
        Most recently fetched :class:`~deapi.data_types.Result`. ``None``
        until the first successful fetch.
    image : numpy.ndarray or None
        Shortcut for ``result.image``.
    histogram : Histogram or None
        Shortcut for ``result.histogram``.
    attributes : Attributes or None
        Shortcut for ``result.attributes``.
    """

    def __init__(
        self,
        client: "Client",
        frame_type: str,
        display_fps: float = 30,
        window_width: int | None = None,
        window_height: int | None = None,
    ):
        self._client = client
        self._frame_type = frame_type
        self._display_fps = display_fps
        self._window_width = window_width
        self._window_height = window_height
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._plot = None
        self._result: "Result | None" = None

    # ── public API ────────────────────────────────────────────────────────────

    @property
    def frame_type(self) -> str:
        """Frame type currently being streamed. Settable at any time."""
        return self._frame_type

    @frame_type.setter
    def frame_type(self, value: str) -> None:
        self._frame_type = value

    @property
    def result(self) -> "Result | None":
        """Most recently fetched Result, or None before the first fetch."""
        return self._result

    @property
    def image(self) -> "np.ndarray | None":
        """Most recent image array, or None."""
        r = self._result
        return r.image if r is not None else None

    @property
    def histogram(self) -> "Histogram | None":
        """Most recent Histogram, or None."""
        r = self._result
        return r.histogram if r is not None else None

    @property
    def attributes(self) -> "Attributes | None":
        """Most recent Attributes, or None."""
        r = self._result
        return r.attributes if r is not None else None

    def plot(self, ax=None):
        """Start streaming and return (or attach) the live anyplotlib display.

        Parameters
        ----------
        ax : anyplotlib.Axes, optional
            Axes to attach the image to. If omitted, a new Figure is created.

        Returns
        -------
        anyplotlib.Figure
            When *ax* is None (standalone).
        anyplotlib.plot2d.Plot2D
            When *ax* is provided (embedded).

        Raises
        ------
        RuntimeError
            If called while a streaming thread is already running.
        """
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError(
                "LiveResult.plot() is already running. Call stop() first."
            )

        initial = self._client.get_result(
            self._frame_type, histogram=Histogram(bins=256), **self._get_kwargs()
        )
        self._result = initial
        initial_data = (
            initial.image if initial.image is not None else np.zeros((64, 64))
        )

        standalone = ax is None
        if standalone:
            import anyplotlib as apl

            fig, ax = apl.subplots(1, 1)

        self._plot = ax.imshow(initial_data)

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

        if standalone:
            return fig
        return self._plot

    def stop(self) -> None:
        """Stop the background streaming thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    # ── internals ─────────────────────────────────────────────────────────────

    def _get_kwargs(self) -> dict:
        kwargs = {}
        if self._window_width is not None:
            kwargs["window_width"] = self._window_width
        if self._window_height is not None:
            kwargs["window_height"] = self._window_height
        return kwargs

    def _run(self) -> None:
        sleep_active = 1.0 / self._display_fps
        was_acquiring = False

        while not self._stop_event.is_set():
            acquiring = self._client.acquiring
            if acquiring or was_acquiring:
                try:
                    result = self._client.get_result(
                        self._frame_type,
                        histogram=Histogram(bins=256),
                        **self._get_kwargs(),
                    )
                    self._result = result
                    if result.image is not None:
                        self._plot.set_data(result.image)
                except Exception:
                    pass
            was_acquiring = acquiring
            if acquiring:
                self._stop_event.wait(sleep_active)
            else:
                self._stop_event.wait(_IDLE_SLEEP)
