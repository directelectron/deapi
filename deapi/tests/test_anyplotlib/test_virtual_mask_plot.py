import numpy as np
import pytest
from unittest.mock import Mock
import anyplotlib as apl
from anyplotlib.plot2d import Plot2D
from anyplotlib.widgets import CircleWidget, AnnularWidget, PolygonWidget
from anyplotlib.callbacks import Event
from skimage.draw import disk as sk_disk, polygon as sk_polygon
from deapi.data_types import VirtualMask


def _make_client(mask, shape_str="Circle"):
    client = Mock()
    client.get_virtual_mask.return_value = mask
    client.__getitem__ = Mock(return_value=shape_str)
    return client


def _circle_mask(cx=64, cy=64, r=20, size=128):
    mask = np.ones((size, size), dtype=np.uint8)
    rr, cc = sk_disk((cy, cx), r, shape=(size, size))
    mask[rr, cc] = 2
    return mask


def _annular_mask(cx=64, cy=64, r_inner=15, r_outer=35, size=128):
    mask = np.ones((size, size), dtype=np.uint8)
    rr_o, cc_o = sk_disk((cy, cx), r_outer, shape=(size, size))
    mask[rr_o, cc_o] = 2
    rr_i, cc_i = sk_disk((cy, cx), r_inner, shape=(size, size))
    mask[rr_i, cc_i] = 1
    return mask


def _polygon_mask(size=128):
    mask = np.ones((size, size), dtype=np.uint8)
    rr, cc = sk_polygon([30, 30, 90, 90], [30, 90, 90, 30], shape=(size, size))
    mask[rr, cc] = 2
    return mask


# ── Standalone / embedded ──────────────────────────────────────────────────────


def test_virtual_mask_plot_standalone_returns_figure():
    client = _make_client(_circle_mask(), "Circle")
    vm = VirtualMask(client=client, index=0)
    fig = vm.plot()
    assert isinstance(fig, apl.Figure)


def test_virtual_mask_plot_embedded_returns_plot2d():
    client = _make_client(_circle_mask(), "Circle")
    vm = VirtualMask(client=client, index=0)
    fig, ax = apl.subplots(1, 1)
    result = vm.plot(ax=ax)
    assert isinstance(result, Plot2D)


# ── Widget type selection ─────────────────────────────────────────────────────


def test_virtual_mask_plot_circle_shape_adds_circle_widget():
    client = _make_client(_circle_mask(), "Circle")
    vm = VirtualMask(client=client, index=0)
    fig, ax = apl.subplots(1, 1)
    plot2d = vm.plot(ax=ax)
    assert any(isinstance(w, CircleWidget) for w in plot2d._widgets.values())


def test_virtual_mask_plot_annular_shape_adds_annular_widget():
    client = _make_client(_annular_mask(), "Annular")
    vm = VirtualMask(client=client, index=0)
    fig, ax = apl.subplots(1, 1)
    plot2d = vm.plot(ax=ax)
    assert any(isinstance(w, AnnularWidget) for w in plot2d._widgets.values())


def test_virtual_mask_plot_polygon_shape_adds_polygon_widget():
    client = _make_client(_polygon_mask(), "Polygon")
    vm = VirtualMask(client=client, index=0)
    fig, ax = apl.subplots(1, 1)
    plot2d = vm.plot(ax=ax)
    assert any(isinstance(w, PolygonWidget) for w in plot2d._widgets.values())


def test_virtual_mask_plot_arbitrary_shape_no_widget():
    client = _make_client(_circle_mask(), "Arbitrary")
    vm = VirtualMask(client=client, index=0)
    fig, ax = apl.subplots(1, 1)
    plot2d = vm.plot(ax=ax)
    assert len(plot2d._widgets) == 0


# ── pointer_up pushes mask to server ──────────────────────────────────────────


def test_virtual_mask_pointer_up_calls_set_virtual_mask():
    mask = _circle_mask()
    client = _make_client(mask, "Circle")
    vm = VirtualMask(client=client, index=0)
    fig, ax = apl.subplots(1, 1)
    plot2d = vm.plot(ax=ax)

    widget = next(iter(plot2d._widgets.values()))
    widget.callbacks.fire(Event(event_type="pointer_up", source=widget))

    client.set_virtual_mask.assert_called_once()
    call_args = client.set_virtual_mask.call_args
    sent_mask = call_args[0][3]
    assert sent_mask.shape == mask.shape
    assert sent_mask.dtype == np.uint8
