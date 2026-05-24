import numpy as np
import pytest
from skimage.draw import disk as sk_disk, polygon as sk_polygon
from deapi.data_types import (
    _extract_circle_geometry,
    _extract_annular_geometry,
    _extract_polygon_geometry,
    _widget_to_mask,
)


# ── _extract_circle_geometry ──────────────────────────────────────────────────


def test_extract_circle_geometry_returns_centroid_and_radius():
    mask = np.ones((128, 128), dtype=np.uint8)
    rr, cc = sk_disk((64, 64), 20, shape=(128, 128))
    mask[rr, cc] = 2
    cx, cy, r = _extract_circle_geometry(mask)
    assert abs(cx - 64) < 2
    assert abs(cy - 64) < 2
    assert abs(r - 20) < 3


def test_extract_circle_geometry_empty_mask_returns_defaults():
    mask = np.ones((128, 128), dtype=np.uint8)
    cx, cy, r = _extract_circle_geometry(mask)
    assert cx == 64.0
    assert cy == 64.0
    assert r > 0


# ── _extract_annular_geometry ─────────────────────────────────────────────────


def test_extract_annular_geometry_returns_inner_outer():
    mask = np.ones((128, 128), dtype=np.uint8)
    rr_o, cc_o = sk_disk((64, 64), 40, shape=(128, 128))
    rr_i, cc_i = sk_disk((64, 64), 15, shape=(128, 128))
    mask[rr_o, cc_o] = 2
    mask[rr_i, cc_i] = 1
    cx, cy, r_inner, r_outer = _extract_annular_geometry(mask)
    assert abs(cx - 64) < 2
    assert abs(cy - 64) < 2
    assert r_inner < r_outer
    assert abs(r_inner - 15) < 5
    assert abs(r_outer - 40) < 5


# ── _extract_polygon_geometry ─────────────────────────────────────────────────


def test_extract_polygon_geometry_returns_vertices():
    mask = np.ones((128, 128), dtype=np.uint8)
    rows = [30, 30, 90, 90]
    cols = [30, 90, 90, 30]
    rr, cc = sk_polygon(rows, cols, shape=(128, 128))
    mask[rr, cc] = 2
    vertices = _extract_polygon_geometry(mask)
    assert len(vertices) >= 3
    assert all(len(v) == 2 for v in vertices)


def test_extract_polygon_geometry_empty_mask_returns_defaults():
    mask = np.ones((128, 128), dtype=np.uint8)
    vertices = _extract_polygon_geometry(mask)
    assert len(vertices) >= 3


# ── _widget_to_mask ───────────────────────────────────────────────────────────


def _make_circle_widget(cx, cy, r):
    from unittest.mock import Mock

    w = Mock()
    w._data = {"type": "circle", "cx": cx, "cy": cy, "r": r}
    w._type = "circle"
    w.cx = cx
    w.cy = cy
    w.r = r
    return w


def _make_annular_widget(cx, cy, r_inner, r_outer):
    from unittest.mock import Mock

    w = Mock()
    w._data = {
        "type": "annular",
        "cx": cx,
        "cy": cy,
        "r_inner": r_inner,
        "r_outer": r_outer,
    }
    w._type = "annular"
    w.cx = cx
    w.cy = cy
    w.r_inner = r_inner
    w.r_outer = r_outer
    return w


def _make_polygon_widget(vertices):
    from unittest.mock import Mock

    w = Mock()
    w._data = {"type": "polygon", "vertices": vertices}
    w._type = "polygon"
    w.vertices = vertices
    return w


def test_widget_to_mask_circle():
    widget = _make_circle_widget(cx=64, cy=64, r=20)
    mask = _widget_to_mask(widget, shape=(128, 128))
    assert mask.shape == (128, 128)
    assert mask[64, 64] == 2
    assert mask[0, 0] == 1


def test_widget_to_mask_annular():
    widget = _make_annular_widget(cx=64, cy=64, r_inner=10, r_outer=30)
    mask = _widget_to_mask(widget, shape=(128, 128))
    assert mask[64, 64] == 1  # inside inner radius → not selected
    assert mask[64, 80] == 2  # inside ring → selected
    assert mask[0, 0] == 1  # outside outer radius → not selected


def test_widget_to_mask_polygon():
    verts = [[30.0, 30.0], [90.0, 30.0], [90.0, 90.0], [30.0, 90.0]]
    widget = _make_polygon_widget(verts)
    mask = _widget_to_mask(widget, shape=(128, 128))
    assert mask[60, 60] == 2  # inside polygon
    assert mask[0, 0] == 1  # outside polygon
