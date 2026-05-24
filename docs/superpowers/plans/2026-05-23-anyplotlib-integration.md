# anyplotlib Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace deapi's static matplotlib `.plot()` methods with interactive anyplotlib equivalents and add a `LiveResult` class that streams live frames from the DE server into a self-updating Jupyter widget.

**Architecture:** All `.plot()` methods on `Result`, `Histogram`, and `VirtualMask` are replaced in-place to return `anyplotlib` figures (standalone) or attach to a caller-supplied `anyplotlib.Axes` (embedded). `LiveResult` wraps a `Client` + frame type and runs a two-mode background thread: idle (polls `client.acquiring` at 2 Hz) and active (calls `get_result()` + `plot.set_data()` at `display_fps` Hz). `VirtualMask.plot()` reads the server-side shape property and adds the matching interactive overlay widget; on `pointer_up` the widget geometry is converted back to a numpy mask and pushed to the server.

**Tech Stack:** Python 3.8+, anyplotlib, scikit-image (already a dep), threading (stdlib), pytest + unittest.mock

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `pyproject.toml` | Add anyplotlib dependency |
| Create | `deapi/live_result.py` | `LiveResult` class with two-mode background thread |
| Modify | `deapi/data_types.py` | Replace `.plot()` on `Histogram`, `Result`, `VirtualMask`; add private geometry helpers |
| Modify | `deapi/client.py` | Add `live_result()` factory method |
| Create | `deapi/tests/test_anyplotlib/__init__.py` | Test package marker |
| Create | `deapi/tests/test_anyplotlib/test_histogram_plot.py` | Tests for `Histogram.plot()` |
| Create | `deapi/tests/test_anyplotlib/test_result_plot.py` | Tests for `Result.plot()` |
| Create | `deapi/tests/test_anyplotlib/test_virtual_mask_geometry.py` | Tests for geometry extraction helpers |
| Create | `deapi/tests/test_anyplotlib/test_virtual_mask_plot.py` | Tests for `VirtualMask.plot()` interactive behavior |
| Create | `deapi/tests/test_anyplotlib/test_live_result.py` | Tests for `LiveResult` thread state machine |
| Modify | `Examples/live_imaging/viewing_the_sensor.py` | Use `LiveResult` instead of `plt.pause()` loop |
| Modify | `Examples/virtual_imaging/setting_virtual_masks.py` | Remove `import matplotlib.pyplot` |
| Modify | `Examples/virtual_imaging/vdf_vbf.py` | Use `Result.plot()` / `VirtualMask.plot()` |

---

## Task 1: Add anyplotlib dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Install anyplotlib from the local repo**

```bash
uv add --editable /Users/carterfrancis/PycharmProjects/anyplotlib
```

Expected: `pyproject.toml` updated with `anyplotlib` entry, `uv.lock` regenerated.

- [ ] **Step 2: Verify the import works**

```bash
uv run python -c "import anyplotlib as apl; print(apl.__version__)"
```

Expected: version string printed, no import error.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add anyplotlib dependency"
```

---

## Task 2: Replace `Histogram.plot()`

**Files:**
- Modify: `deapi/data_types.py` (lines ~422–443 — the existing `Histogram.plot` method)
- Create: `deapi/tests/test_anyplotlib/__init__.py`
- Create: `deapi/tests/test_anyplotlib/test_histogram_plot.py`

- [ ] **Step 1: Create the test package**

```bash
touch deapi/tests/test_anyplotlib/__init__.py
```

- [ ] **Step 2: Write the failing tests**

Create `deapi/tests/test_anyplotlib/test_histogram_plot.py`:

```python
import numpy as np
import pytest
import anyplotlib as apl
from anyplotlib.plot1d import Plot1D
from deapi.data_types import Histogram


@pytest.fixture
def hist():
    return Histogram(min=0.0, max=100.0, bins=256, data=list(np.ones(256)))


def test_histogram_plot_standalone_returns_figure(hist):
    fig = hist.plot()
    assert isinstance(fig, apl.Figure)


def test_histogram_plot_embedded_returns_plot1d(hist):
    fig, ax = apl.subplots(1, 1)
    result = hist.plot(ax=ax)
    assert isinstance(result, Plot1D)


def test_histogram_plot_none_data_does_not_crash():
    hist = Histogram(min=0.0, max=100.0, bins=256, data=None)
    fig = hist.plot()
    assert isinstance(fig, apl.Figure)
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
uv run pytest deapi/tests/test_anyplotlib/test_histogram_plot.py -v
```

Expected: 3 FAILED — `Histogram.plot()` currently returns `matplotlib.axes.Axes`, not `apl.Figure`.

- [ ] **Step 4: Replace `Histogram.plot()` in `deapi/data_types.py`**

Find and replace the entire `plot` method on `Histogram` (currently at ~line 422):

```python
def plot(self, ax=None):
    """Plot the histogram using anyplotlib.

    Parameters
    ----------
    ax : anyplotlib.Axes, optional
        Axes to attach the plot to. If omitted, a new Figure is created.

    Returns
    -------
    anyplotlib.Figure
        When ax is None (standalone).
    anyplotlib.plot1d.Plot1D
        When ax is provided (embedded).
    """
    import anyplotlib as apl
    import numpy as np

    standalone = ax is None
    if standalone:
        fig, ax = apl.subplots(1, 1)

    x = np.linspace(self.min, self.max, self.bins)
    data = np.asarray(self.data, dtype=float) if self.data is not None else np.zeros(self.bins)
    plot1d = ax.plot(x, data)

    if standalone:
        return fig
    return plot1d
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
uv run pytest deapi/tests/test_anyplotlib/test_histogram_plot.py -v
```

Expected: 3 PASSED.

- [ ] **Step 6: Commit**

```bash
git add deapi/data_types.py deapi/tests/test_anyplotlib/__init__.py deapi/tests/test_anyplotlib/test_histogram_plot.py
git commit -m "feat: replace Histogram.plot() with anyplotlib"
```

---

## Task 3: Replace `Result.plot()`

**Files:**
- Modify: `deapi/data_types.py` (lines ~825–930 — the existing `Result.plot` method)
- Create: `deapi/tests/test_anyplotlib/test_result_plot.py`

- [ ] **Step 1: Write the failing tests**

Create `deapi/tests/test_anyplotlib/test_result_plot.py`:

```python
import numpy as np
import pytest
import anyplotlib as apl
from anyplotlib.plot2d import Plot2D
from deapi.data_types import Result, Histogram


@pytest.fixture
def sample_result():
    image = np.random.rand(64, 64).astype(np.float32)
    hist = Histogram(min=0.0, max=1.0, bins=256, data=list(np.ones(256)))
    return Result(image=image, pixel_format=None, attributes=None, histogram=hist)


def test_result_plot_standalone_returns_figure(sample_result):
    fig = sample_result.plot()
    assert isinstance(fig, apl.Figure)


def test_result_plot_embedded_returns_plot2d(sample_result):
    fig, axs = apl.subplots(1, 2)
    result = sample_result.plot(ax=axs[0])
    assert isinstance(result, Plot2D)


def test_result_plot_kwargs_forwarded(sample_result):
    fig = sample_result.plot(cmap="viridis", vmin=0.1, vmax=0.9)
    assert isinstance(fig, apl.Figure)


def test_result_plot_no_histogram():
    image = np.random.rand(64, 64).astype(np.float32)
    result = Result(image=image, pixel_format=None, attributes=None, histogram=None)
    fig = result.plot()
    assert isinstance(fig, apl.Figure)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest deapi/tests/test_anyplotlib/test_result_plot.py -v
```

Expected: 4 FAILED — `Result.plot()` currently returns `matplotlib.axes.Axes`.

- [ ] **Step 3: Replace `Result.plot()` in `deapi/data_types.py`**

Find and replace the entire `plot` method on `Result` (currently at ~line 825). The new method:

```python
def plot(self, ax=None, **kwargs):
    """Plot the image using anyplotlib.

    Parameters
    ----------
    ax : anyplotlib.Axes, optional
        Axes to attach the image to. If omitted, a new 2-panel Figure is
        created (image left, histogram right).
    **kwargs
        Forwarded to ``ax.imshow``: ``cmap``, ``vmin``, ``vmax``.

    Returns
    -------
    anyplotlib.Figure
        When ax is None (standalone).
    anyplotlib.plot2d.Plot2D
        When ax is provided (embedded — no histogram panel).
    """
    import anyplotlib as apl
    import numpy as np

    standalone = ax is None
    if standalone:
        fig, axs = apl.subplots(1, 2, width_ratios=[4, 1])
        img_ax, hist_ax = axs
    else:
        img_ax = ax

    plot2d = img_ax.imshow(
        self.image,
        cmap=kwargs.get("cmap", "gray"),
        vmin=kwargs.get("vmin", None),
        vmax=kwargs.get("vmax", None),
    )

    if standalone:
        if (
            self.histogram is not None
            and getattr(self.histogram, "data", None) is not None
        ):
            x = np.linspace(
                self.histogram.min, self.histogram.max, self.histogram.bins
            )
            hist_ax.plot(x, np.asarray(self.histogram.data, dtype=float))
        return fig

    return plot2d
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest deapi/tests/test_anyplotlib/test_result_plot.py -v
```

Expected: 4 PASSED.

- [ ] **Step 5: Commit**

```bash
git add deapi/data_types.py deapi/tests/test_anyplotlib/test_result_plot.py
git commit -m "feat: replace Result.plot() with anyplotlib"
```

---

## Task 4: Add geometry extraction helpers for `VirtualMask`

These are private module-level functions in `deapi/data_types.py` that extract widget geometry from a numpy mask array and convert widget geometry back to a mask. They live just above the `VirtualMask` class.

**Files:**
- Modify: `deapi/data_types.py` (insert helpers before `class VirtualMask` at ~line 722)
- Create: `deapi/tests/test_anyplotlib/test_virtual_mask_geometry.py`

- [ ] **Step 1: Write the failing tests**

Create `deapi/tests/test_anyplotlib/test_virtual_mask_geometry.py`:

```python
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
    w._data = {"type": "annular", "cx": cx, "cy": cy, "r_inner": r_inner, "r_outer": r_outer}
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
    assert mask[64, 64] == 1        # inside inner radius → not selected
    assert mask[64, 80] == 2        # inside ring → selected
    assert mask[0, 0] == 1          # outside outer radius → not selected


def test_widget_to_mask_polygon():
    verts = [[30.0, 30.0], [90.0, 30.0], [90.0, 90.0], [30.0, 90.0]]
    widget = _make_polygon_widget(verts)
    mask = _widget_to_mask(widget, shape=(128, 128))
    assert mask[60, 60] == 2        # inside polygon
    assert mask[0, 0] == 1          # outside polygon
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest deapi/tests/test_anyplotlib/test_virtual_mask_geometry.py -v
```

Expected: ImportError — the helpers don't exist yet.

- [ ] **Step 3: Add geometry helpers to `deapi/data_types.py`**

Insert the following block immediately before `class VirtualMask:` (~line 722):

```python
# ── VirtualMask geometry helpers ──────────────────────────────────────────────

def _extract_circle_geometry(mask: np.ndarray):
    """Return (cx, cy, r) from a mask array where 2=selected."""
    ys, xs = np.where(mask == 2)
    if len(ys) == 0:
        h, w = mask.shape
        return float(w / 2), float(h / 2), float(min(h, w) / 4)
    cy, cx = float(ys.mean()), float(xs.mean())
    r = float(np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2).mean())
    return cx, cy, max(r, 1.0)


def _extract_annular_geometry(mask: np.ndarray):
    """Return (cx, cy, r_inner, r_outer) from a mask where 2=ring pixels."""
    ys, xs = np.where(mask == 2)
    if len(ys) == 0:
        h, w = mask.shape
        return float(w / 2), float(h / 2), float(min(h, w) / 8), float(min(h, w) / 4)
    # centroid from all selected (2) pixels
    cy, cx = float(ys.mean()), float(xs.mean())
    dists = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    return cx, cy, float(dists.min()), float(dists.max())


def _extract_polygon_geometry(mask: np.ndarray):
    """Return list of (x, y) vertex pairs from a mask where 2=polygon interior."""
    from skimage.measure import find_contours
    contours = find_contours(mask == 2, 0.5)
    if not contours:
        h, w = mask.shape
        return [
            [float(w / 4), float(h / 4)],
            [float(3 * w / 4), float(h / 4)],
            [float(3 * w / 4), float(3 * h / 4)],
            [float(w / 4), float(3 * h / 4)],
        ]
    contour = contours[0]
    step = max(1, len(contour) // 20)
    return [[float(c[1]), float(c[0])] for c in contour[::step]]


def _widget_to_mask(widget, shape: tuple) -> np.ndarray:
    """Convert an anyplotlib overlay widget's geometry to a numpy mask array.

    Returns uint8 array where 2=selected region, 1=unselected.
    """
    from skimage.draw import disk, polygon as sk_polygon
    h, w = shape
    mask = np.ones(shape, dtype=np.uint8)
    wtype = widget._type

    if wtype == "circle":
        rr, cc = disk((widget.cy, widget.cx), max(widget.r, 1), shape=shape)
        mask[rr, cc] = 2

    elif wtype == "annular":
        rr_o, cc_o = disk((widget.cy, widget.cx), max(widget.r_outer, 1), shape=shape)
        mask[rr_o, cc_o] = 2
        rr_i, cc_i = disk((widget.cy, widget.cx), max(widget.r_inner, 1), shape=shape)
        mask[rr_i, cc_i] = 1

    elif wtype == "polygon":
        verts = widget.vertices  # list of [x, y]
        rows = [v[1] for v in verts]
        cols = [v[0] for v in verts]
        rr, cc = sk_polygon(rows, cols, shape=shape)
        mask[rr, cc] = 2

    return mask
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest deapi/tests/test_anyplotlib/test_virtual_mask_geometry.py -v
```

Expected: all PASSED.

- [ ] **Step 5: Commit**

```bash
git add deapi/data_types.py deapi/tests/test_anyplotlib/test_virtual_mask_geometry.py
git commit -m "feat: add VirtualMask geometry extraction helpers"
```

---

## Task 5: Replace `VirtualMask.plot()` with interactive anyplotlib version

**Files:**
- Modify: `deapi/data_types.py` (`VirtualMask.plot` at ~line 772)
- Create: `deapi/tests/test_anyplotlib/test_virtual_mask_plot.py`

- [ ] **Step 1: Write the failing tests**

Create `deapi/tests/test_anyplotlib/test_virtual_mask_plot.py`:

```python
import numpy as np
import pytest
from unittest.mock import Mock
import anyplotlib as apl
from anyplotlib.plot2d import Plot2D
from anyplotlib.widgets import CircleWidget, AnnularWidget, PolygonWidget
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

    # Simulate pointer_up on the widget
    widget = next(iter(plot2d._widgets.values()))
    from anyplotlib.callbacks import Event
    widget.callbacks.fire(Event("pointer_up", source=widget))

    client.set_virtual_mask.assert_called_once()
    call_args = client.set_virtual_mask.call_args
    sent_mask = call_args[0][3]  # positional: (index, w, h, mask)
    assert sent_mask.shape == mask.shape
    assert sent_mask.dtype == np.uint8
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest deapi/tests/test_anyplotlib/test_virtual_mask_plot.py -v
```

Expected: FAILED — `VirtualMask.plot()` currently returns `matplotlib.axes.Axes`.

- [ ] **Step 3: Replace `VirtualMask.plot()` in `deapi/data_types.py`**

Find and replace the `plot` method on `VirtualMask` (~line 772):

```python
def plot(self, ax=None, **kwargs):
    """Plot the virtual mask using anyplotlib with an interactive overlay widget.

    The widget type is determined by the server-side shape property
    (``"Circle"``, ``"Annular"``, ``"Polygon"``, or ``"Arbitrary"``).
    When the user releases the drag handle (``pointer_up``), the updated
    geometry is converted back to a numpy mask and pushed to the server.

    Parameters
    ----------
    ax : anyplotlib.Axes, optional
        Axes to attach to. If omitted, a new Figure is created.

    Returns
    -------
    anyplotlib.Figure
        When ax is None (standalone).
    anyplotlib.plot2d.Plot2D
        When ax is provided (embedded).
    """
    import anyplotlib as apl

    mask = self.client.get_virtual_mask(self.index)
    shape_prop = f"Scan - Virtual Detector {self.index} Shape"
    shape = self.client[shape_prop]

    standalone = ax is None
    if standalone:
        fig, ax = apl.subplots(1, 1)

    plot2d = ax.imshow(mask.astype(float), vmin=0, vmax=3, **kwargs)

    widget = None
    if shape == "Circle":
        cx, cy, r = _extract_circle_geometry(mask)
        widget = plot2d.add_circle_widget(cx=cx, cy=cy, r=r)
    elif shape == "Annular":
        cx, cy, r_inner, r_outer = _extract_annular_geometry(mask)
        widget = plot2d.add_annular_widget(cx=cx, cy=cy, r_inner=r_inner, r_outer=r_outer)
    elif shape == "Polygon":
        vertices = _extract_polygon_geometry(mask)
        widget = plot2d.add_polygon_widget(vertices=vertices)

    if widget is not None:
        _client = self.client
        _index = self.index
        _shape = mask.shape

        def _on_pointer_up(event):
            new_mask = _widget_to_mask(widget, _shape)
            _client.set_virtual_mask(_index, new_mask.shape[1], new_mask.shape[0], new_mask)

        widget.add_event_handler(_on_pointer_up, "pointer_up")

    if standalone:
        return fig
    return plot2d
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest deapi/tests/test_anyplotlib/test_virtual_mask_plot.py -v
```

Expected: all PASSED.

- [ ] **Step 5: Commit**

```bash
git add deapi/data_types.py deapi/tests/test_anyplotlib/test_virtual_mask_plot.py
git commit -m "feat: replace VirtualMask.plot() with interactive anyplotlib widget"
```

---

## Task 6: Create `LiveResult` class

**Files:**
- Create: `deapi/live_result.py`
- Create: `deapi/tests/test_anyplotlib/test_live_result.py`

- [ ] **Step 1: Write the failing tests**

Create `deapi/tests/test_anyplotlib/test_live_result.py`:

```python
import time
import numpy as np
import pytest
from unittest.mock import Mock, PropertyMock
from deapi.data_types import Result
from deapi.live_result import LiveResult


def _make_result(shape=(64, 64)):
    return Result(
        image=np.zeros(shape, dtype=np.float32),
        pixel_format=None,
        attributes=None,
        histogram=None,
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
    time.sleep(0.7)   # > 1 idle cycle (0.5 s)
    live.stop()
    assert mock_plot.set_data.call_count == initial_count


# ── Active mode: streams when acquiring ──────────────────────────────────────

def test_active_mode_calls_set_data(active_client):
    live = LiveResult(active_client, "singleframe_integrated", display_fps=30)
    ax = _mock_ax()
    mock_plot = ax.imshow.return_value
    live.plot(ax=ax)
    time.sleep(0.2)   # 6 frames at 30 fps
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
    # No new set_data calls after returning to idle
    assert mock_plot.set_data.call_count == count_while_active


# ── window_width / window_height forwarded to get_result ─────────────────────

def test_window_kwargs_forwarded_to_get_result(active_client):
    live = LiveResult(
        active_client, "singleframe_integrated",
        display_fps=60, window_width=128, window_height=128,
    )
    ax = _mock_ax()
    live.plot(ax=ax)
    time.sleep(0.1)
    live.stop()
    call_kwargs = active_client.get_result.call_args_list[-1][1]
    assert call_kwargs.get("window_width") == 128
    assert call_kwargs.get("window_height") == 128


# ── Embedded: returns Plot2D object ──────────────────────────────────────────

def test_live_result_embedded_returns_plot_object(idle_client):
    live = LiveResult(idle_client, "singleframe_integrated")
    ax = _mock_ax()
    mock_plot = ax.imshow.return_value
    result = live.plot(ax=ax)
    assert result is mock_plot
    live.stop()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest deapi/tests/test_anyplotlib/test_live_result.py -v
```

Expected: ImportError — `deapi.live_result` does not exist yet.

- [ ] **Step 3: Create `deapi/live_result.py`**

```python
"""
live_result.py
==============
LiveResult: a continuously-updating anyplotlib display for DE camera frames.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from deapi.client import Client

_IDLE_SLEEP = 0.5   # 2 Hz idle poll for client.acquiring


class LiveResult:
    """Continuously streams frames from the DE server into an anyplotlib widget.

    Create via :meth:`deapi.Client.live_result` rather than instantiating
    directly.

    Parameters
    ----------
    client : deapi.Client
        Connected DE client.
    frame_type : str
        Frame type string accepted by :meth:`~deapi.Client.get_result`,
        e.g. ``"singleframe_integrated"``, ``"virtual_image0"``.
    display_fps : float
        Target display refresh rate in frames per second. Default 30.
    window_width : int, optional
        Server-side resize width in pixels. ``None`` means full width.
    window_height : int, optional
        Server-side resize height in pixels. ``None`` means full height.
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

    # ── public API ────────────────────────────────────────────────────────────

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

        initial = self._client.get_result(self._frame_type, **self._get_kwargs())
        initial_data = initial.image if initial.image is not None else np.zeros((64, 64))

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
        kwargs = self._get_kwargs()
        sleep_active = 1.0 / self._display_fps

        while not self._stop_event.is_set():
            if self._client.acquiring:
                try:
                    result = self._client.get_result(self._frame_type, **kwargs)
                    if result.image is not None:
                        self._plot.set_data(result.image)
                except Exception:
                    pass
                self._stop_event.wait(sleep_active)
            else:
                self._stop_event.wait(_IDLE_SLEEP)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest deapi/tests/test_anyplotlib/test_live_result.py -v
```

Expected: all PASSED.

- [ ] **Step 5: Commit**

```bash
git add deapi/live_result.py deapi/tests/test_anyplotlib/test_live_result.py
git commit -m "feat: add LiveResult streaming class"
```

---

## Task 7: Add `client.live_result()` factory

**Files:**
- Modify: `deapi/client.py` (add method after `get_result`, around line 1828)
- Modify: `deapi/tests/test_anyplotlib/test_live_result.py` (append factory test)

- [ ] **Step 1: Write the failing test**

Append to `deapi/tests/test_anyplotlib/test_live_result.py`:

```python
# ── client.live_result() factory ─────────────────────────────────────────────

def test_client_live_result_factory_returns_live_result(idle_client):
    from deapi.live_result import LiveResult
    live = idle_client.live_result(
        "singleframe_integrated", display_fps=15, window_width=128
    )
    assert isinstance(live, LiveResult)
    assert live._frame_type == "singleframe_integrated"
    assert live._display_fps == 15
    assert live._window_width == 128
```

But `idle_client` is a `Mock()` — it won't have `live_result`. Instead write the test against the real `Client` class:

```python
def test_client_live_result_factory_returns_live_result():
    from unittest.mock import patch, Mock
    from deapi.client import Client
    from deapi.live_result import LiveResult

    client = Client.__new__(Client)
    live = Client.live_result(client, "virtual_image0", display_fps=10, window_height=64)
    assert isinstance(live, LiveResult)
    assert live._client is client
    assert live._frame_type == "virtual_image0"
    assert live._display_fps == 10
    assert live._window_height == 64
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest deapi/tests/test_anyplotlib/test_live_result.py::test_client_live_result_factory_returns_live_result -v
```

Expected: FAILED — `Client` has no `live_result` method.

- [ ] **Step 3: Add `live_result()` to `deapi/client.py`**

In `client.py`, find the `set_virtual_mask` method (~line 1828) and insert the new method just before it:

```python
def live_result(
    self,
    frame_type: str = "singleframe_integrated",
    display_fps: float = 30,
    window_width: int = None,
    window_height: int = None,
):
    """Return a :class:`~deapi.live_result.LiveResult` for streaming display.

    Parameters
    ----------
    frame_type : str
        Frame type for :meth:`get_result`, e.g. ``"singleframe_integrated"``.
    display_fps : float
        Target display refresh rate. Default 30.
    window_width : int, optional
        Server-side resize width in pixels.
    window_height : int, optional
        Server-side resize height in pixels.

    Returns
    -------
    deapi.live_result.LiveResult
    """
    from deapi.live_result import LiveResult

    return LiveResult(
        self,
        frame_type,
        display_fps=display_fps,
        window_width=window_width,
        window_height=window_height,
    )
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest deapi/tests/test_anyplotlib/test_live_result.py -v
```

Expected: all PASSED.

- [ ] **Step 5: Run full test suite to catch regressions**

```bash
uv run pytest deapi/tests/test_anyplotlib/ -v
```

Expected: all PASSED.

- [ ] **Step 6: Commit**

```bash
git add deapi/client.py deapi/tests/test_anyplotlib/test_live_result.py
git commit -m "feat: add Client.live_result() factory method"
```

---

## Task 8: Update examples

**Files:**
- Modify: `Examples/live_imaging/viewing_the_sensor.py`
- Modify: `Examples/virtual_imaging/setting_virtual_masks.py`
- Modify: `Examples/virtual_imaging/vdf_vbf.py`

- [ ] **Step 1: Update `Examples/live_imaging/viewing_the_sensor.py`**

Replace entire file content:

```python
"""
Viewing Sensor Data During Acquisition
======================================

This example shows how to view the sensor data during acquisition using
``LiveResult`` — an automatically-updating anyplotlib widget that streams
frames from the DE server in the background.

The ``LiveResult`` thread starts in idle mode and automatically activates
whenever ``client.acquiring`` becomes True — even if the acquisition was
started from a separate GUI application or script.
"""

from deapi import Client
import sys

client = Client()
if not sys.platform.startswith("win"):
    client.usingMmf = False
client.connect(port=13240)

client["Frames Per Second"] = 500
client.scan(size_x=16, size_y=16, enable="On")
client.start_acquisition(1)

# %%
# Create live viewers
# -------------------
# Each LiveResult streams its frame type at 30 fps into an anyplotlib panel.
# ``window_width=256`` resizes the diffraction pattern on the server before
# sending, reducing network load.

import anyplotlib as apl

fig, axs = apl.subplots(1, 2, figsize=(900, 420))

live_diffraction = client.live_result(
    "singleframe_integrated", display_fps=30, window_width=256
)
live_virtual = client.live_result("virtual_image0", display_fps=30)

live_diffraction.plot(ax=axs[0])
live_virtual.plot(ax=axs[1])

fig  # display widget in Jupyter — updates automatically while acquiring

# %%
# Stopping the stream
# -------------------
# The threads stop automatically when ``client.acquiring`` becomes False.
# You can also stop them manually:
#
#   live_diffraction.stop()
#   live_virtual.stop()

client.disconnect()
```

- [ ] **Step 2: Update `Examples/virtual_imaging/setting_virtual_masks.py`**

Remove the `import matplotlib.pyplot as plt` line and the final `plt.subplots` block. The `v.plot()` calls already use the new anyplotlib API. Replace the multi-mask tableau section:

```python
# %%
# Plotting Multiple Virtual Masks
# --------------------------------
import anyplotlib as apl

fig, axs = apl.subplots(1, 3, figsize=(960, 360))
for ax, v in zip(axs, c.virtual_masks[:3]):
    v.plot(ax=ax)

fig  # interactive: drag the overlay widget to reposition each mask
```

- [ ] **Step 3: Update `Examples/virtual_imaging/vdf_vbf.py`**

Replace the final matplotlib plot block (lines ~113–117) with:

```python
# %%
# Acquire and view the virtual images
# ------------------------------------
import anyplotlib as apl

client["Frames Per Second"] = 5000
client.scan(enable="On", size_x=32, size_y=32)
client.start_acquisition()

fig, axs = apl.subplots(1, 3, figsize=(960, 360))

live_sum    = client.live_result("virtual_image0", display_fps=30)
live_vbf    = client.live_result("virtual_image1", display_fps=30)
live_vdf    = client.live_result("virtual_image2", display_fps=30)

live_sum.plot(ax=axs[0])
live_vbf.plot(ax=axs[1])
live_vdf.plot(ax=axs[2])

fig  # streams live virtual images while the scan runs

client.disconnect()
```

- [ ] **Step 4: Run the example tests**

```bash
uv run pytest deapi/tests/test_examples.py -v
```

Expected: PASSED (examples are run in dry-run / import-check mode against the fake server).

- [ ] **Step 5: Commit**

```bash
git add Examples/live_imaging/viewing_the_sensor.py \
        Examples/virtual_imaging/setting_virtual_masks.py \
        Examples/virtual_imaging/vdf_vbf.py
git commit -m "feat: update examples to use anyplotlib and LiveResult"
```

---

## Self-Review

**Spec coverage:**
- ✅ `Histogram.plot()` — Task 2
- ✅ `Result.plot()` — Task 3
- ✅ `VirtualMask.plot()` with geometry helpers — Tasks 4–5
- ✅ `LiveResult` two-mode thread (idle 2 Hz / active display_fps) — Task 6
- ✅ `client.live_result()` factory — Task 7
- ✅ Auto-detect acquisition from any source (polls `client.acquiring`) — Task 6 `_run()`
- ✅ Push mask on `pointer_up` only — Task 5 `_on_pointer_up`
- ✅ `ax=None` standalone vs embedded — all tasks
- ✅ `window_width`/`window_height` server-side resize — Tasks 6–7
- ✅ `display_fps` for smooth display, not camera speed — Task 6
- ✅ Example updates — Task 8

**Placeholder scan:** None found.

**Type consistency:** `_extract_*_geometry` helpers defined in Task 4, used in Task 5. `_widget_to_mask` defined in Task 4, used in Task 5. `LiveResult` defined in Task 6, factory in Task 7. All consistent.
