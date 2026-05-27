import time
import numpy as np
import pytest
from unittest.mock import Mock, PropertyMock
from deapi.data_types import Attributes, Histogram, Result
from deapi.live_result import LiveResult


def _make_result(shape=(64, 64)):
    hist = Histogram(min=0.0, max=1.0, bins=256, data=list(range(256)))
    attrs = Attributes(image_min=0.0, image_max=1.0)
    return Result(
        image=np.zeros(shape, dtype=np.float32),
        pixel_format=None,
        attributes=attrs,
        histogram=hist,
    )


@pytest.fixture
def idle_client():
    client = Mock()
    type(client).acquiring = PropertyMock(return_value=False)
    client.get_result.return_value = _make_result()
    return client


@pytest.fixture
def active_client():
    client = Mock()
    type(client).acquiring = PropertyMock(return_value=True)
    client.get_result.return_value = _make_result()
    return client


def _mock_ax():
    ax = Mock()
    ax.imshow.return_value = Mock()
    return ax


# ── Thread lifecycle ──────────────────────────────────────────────────────────


def test_live_result_plot_starts_thread(idle_client):
    live = LiveResult(idle_client, "singleframe_integrated")
    ax = _mock_ax()
    live.plot(ax=ax)
    assert live._thread is not None
    assert live._thread.is_alive()
    live.stop()


def test_live_result_stop_kills_thread(idle_client):
    live = LiveResult(idle_client, "singleframe_integrated")
    ax = _mock_ax()
    live.plot(ax=ax)
    live.stop()
    assert not live._thread.is_alive()


def test_live_result_plot_twice_raises(idle_client):
    live = LiveResult(idle_client, "singleframe_integrated")
    ax = _mock_ax()
    live.plot(ax=ax)
    with pytest.raises(RuntimeError, match="already running"):
        live.plot(ax=_mock_ax())
    live.stop()


# ── Idle mode: does not stream when not acquiring ─────────────────────────────


def test_idle_mode_does_not_call_set_data(idle_client):
    live = LiveResult(idle_client, "singleframe_integrated", display_fps=30)
    ax = _mock_ax()
    mock_plot = ax.imshow.return_value
    live.plot(ax=ax)
    initial_count = mock_plot.set_data.call_count
    time.sleep(0.7)  # > 1 idle cycle (0.5 s)
    live.stop()
    assert mock_plot.set_data.call_count == initial_count


# ── Active mode: streams when acquiring ──────────────────────────────────────


def test_active_mode_calls_set_data(active_client):
    live = LiveResult(active_client, "singleframe_integrated", display_fps=30)
    ax = _mock_ax()
    mock_plot = ax.imshow.return_value
    live.plot(ax=ax)
    time.sleep(0.2)  # ~6 frames at 30 fps
    live.stop()
    assert mock_plot.set_data.call_count > 0


# ── Transition: idle → active → idle ─────────────────────────────────────────


def test_idle_to_active_transition():
    client = Mock()
    acquiring = PropertyMock(return_value=False)
    type(client).acquiring = acquiring
    client.get_result.return_value = _make_result()

    live = LiveResult(client, "singleframe_integrated", display_fps=30)
    ax = _mock_ax()
    mock_plot = ax.imshow.return_value
    live.plot(ax=ax)

    time.sleep(0.2)
    assert mock_plot.set_data.call_count == 0  # still idle

    acquiring.return_value = True
    time.sleep(0.3)
    count_while_active = mock_plot.set_data.call_count
    assert count_while_active > 0

    acquiring.return_value = False
    time.sleep(0.3)
    live.stop()
    assert mock_plot.set_data.call_count == count_while_active


# ── window_width / window_height forwarded to get_result ─────────────────────


def test_window_kwargs_forwarded_to_get_result(active_client):
    live = LiveResult(
        active_client,
        "singleframe_integrated",
        display_fps=60,
        window_width=128,
        window_height=128,
    )
    ax = _mock_ax()
    live.plot(ax=ax)
    time.sleep(0.1)
    live.stop()
    call_kwargs = active_client.get_result.call_args_list[-1][1]
    assert call_kwargs.get("window_width") == 128
    assert call_kwargs.get("window_height") == 128


# ── Embedded: returns plot object ────────────────────────────────────────────


def test_live_result_embedded_returns_plot_object(idle_client):
    live = LiveResult(idle_client, "singleframe_integrated")
    ax = _mock_ax()
    mock_plot = ax.imshow.return_value
    result = live.plot(ax=ax)
    assert result is mock_plot
    live.stop()


# ── client.live_result() factory ─────────────────────────────────────────────


def test_client_live_result_factory_returns_live_result():
    from deapi.client import Client

    client = Client.__new__(Client)
    live = Client.live_result(
        client, "virtual_image0", display_fps=10, window_height=64
    )
    assert isinstance(live, LiveResult)
    assert live._client is client
    assert live._frame_type == "virtual_image0"
    assert live._display_fps == 10
    assert live._window_height == 64


# ── frame_type property ───────────────────────────────────────────────────────


def test_frame_type_readable(idle_client):
    live = LiveResult(idle_client, "singleframe_integrated")
    assert live.frame_type == "singleframe_integrated"


def test_frame_type_settable(idle_client):
    live = LiveResult(idle_client, "singleframe_integrated")
    live.frame_type = "virtual_image0"
    assert live.frame_type == "virtual_image0"


def test_frame_type_change_used_on_next_fetch(active_client):
    live = LiveResult(active_client, "singleframe_integrated", display_fps=30)
    ax = _mock_ax()
    live.plot(ax=ax)
    live.frame_type = "virtual_image0"
    time.sleep(0.15)
    live.stop()
    last_call = active_client.get_result.call_args_list[-1]
    assert last_call[0][0] == "virtual_image0"


# ── result / image / histogram / attributes properties ───────────────────────


def test_result_none_before_plot(idle_client):
    live = LiveResult(idle_client, "singleframe_integrated")
    assert live.result is None
    assert live.image is None
    assert live.histogram is None
    assert live.attributes is None


def test_result_populated_after_plot(idle_client):
    live = LiveResult(idle_client, "singleframe_integrated")
    ax = _mock_ax()
    live.plot(ax=ax)
    live.stop()
    assert live.result is not None
    assert live.image is not None
    assert live.histogram is not None
    assert live.attributes is not None


def test_result_updated_while_active(active_client):
    live = LiveResult(active_client, "singleframe_integrated", display_fps=30)
    ax = _mock_ax()
    live.plot(ax=ax)
    time.sleep(0.15)
    live.stop()
    assert live.result is not None
    assert live.image is not None


def test_histogram_has_data(active_client):
    live = LiveResult(active_client, "singleframe_integrated", display_fps=30)
    ax = _mock_ax()
    live.plot(ax=ax)
    time.sleep(0.15)
    live.stop()
    assert live.histogram is not None
    assert live.histogram.data is not None


def test_get_result_called_with_histogram(active_client):
    live = LiveResult(active_client, "singleframe_integrated", display_fps=60)
    ax = _mock_ax()
    live.plot(ax=ax)
    time.sleep(0.1)
    live.stop()
    last_call = active_client.get_result.call_args_list[-1]
    hist_arg = last_call[1].get("histogram")
    assert hist_arg is not None
    assert hist_arg.bins == 256
