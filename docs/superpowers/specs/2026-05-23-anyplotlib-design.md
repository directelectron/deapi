# anyplotlib Integration Design

**Date:** 2026-05-23
**Branch:** anyplotlib
**Status:** Approved

## Overview

Replace deapi's static matplotlib `.plot()` methods with interactive anyplotlib-backed equivalents, and introduce a `LiveResult` class that continuously streams frames from the DE server into a self-updating display. All plot methods accept an optional `ax` argument so individual panels can be embedded into user-assembled anyplotlib layouts.

## Goals

- `Result.plot()`, `VirtualMask.plot()`, and `Histogram.plot()` return anyplotlib figures instead of matplotlib figures.
- `VirtualMask.plot()` renders an interactive overlay widget (circle, annular, polygon) that pushes the updated mask to the server on `pointer_up`.
- `LiveResult` streams frames at a configurable display rate (default 30 fps) using a two-mode background thread that auto-detects acquisition start/stop from any source (including external GUI applications).
- All components are composable: pass `ax=<anyplotlib Axes>` to embed into any user-defined layout.

## Non-Goals

- No freehand drawing for `"Arbitrary"` mask shapes — those are shown as a static heatmap only.
- No replacement of the existing `client.start_acquisition()` flow — `LiveResult` is a display layer only.
- No support for non-Jupyter environments (plain scripts still work but widgets won't render).

## Components

### 1. `Result.plot(ax=None, **kwargs)` — `deapi/data_types.py`

**Standalone (ax=None):** Creates a 2-panel anyplotlib figure via `apl.subplots(1, 2)`. Left panel is a `Plot2D` of the image data. Right panel is a `Plot1D` of the histogram.

**Embedded (ax provided):** Attaches only the `Plot2D` to the supplied axes cell. No histogram — the user controls the surrounding layout.

Replaces the existing matplotlib `gridspec`-based implementation. `**kwargs` (e.g. `cmap`, `vmin`, `vmax`) pass through to `Plot2D`.

### 2. `Histogram.plot(ax=None)` — `deapi/data_types.py`

**Standalone:** Creates a single-panel anyplotlib figure with a `Plot1D`.

**Embedded:** Attaches `Plot1D` to the supplied axes cell.

Replaces the existing matplotlib line plot implementation.

### 3. `VirtualMask.plot(ax=None, **kwargs)` — `deapi/data_types.py`

On call, fetches:
- Current mask array via `client.get_virtual_mask(index)` → numpy array sized to current hardware ROI
- Shape property: `client["Scan - Virtual Detector {index} Shape"]`

Renders the mask as a `Plot2D`. Adds an interactive overlay widget based on shape:

| Shape property | Widget | Initial geometry |
|---|---|---|
| `"Circle"` | `add_circle_widget(cx, cy, r)` | Centroid of mask==2 pixels; r = mean distance from centroid to mask==2 pixels |
| `"Annular"` | `add_annular_widget(cx, cy, r_inner, r_outer)` | Centroid of all non-1 pixels; r_inner/r_outer = min/max distance from centroid to mask==2 pixels |
| `"Polygon"` | `add_polygon_widget(vertices=[...])` | Contour extracted via `skimage.measure.find_contours` on mask==2 region |
| `"Arbitrary"` | None | Raw mask shown as heatmap, no widget |

On `pointer_up` on any widget, converts widget geometry back to a numpy mask using `skimage.draw`:
- **Circle**: `disk((cy, cx), r)` → pixels set to 2, remainder to 1
- **Annular**: outer `disk` minus inner `disk` → ring pixels to 2, inner and outer to 1
- **Polygon**: `skimage.draw.polygon(rows, cols)` → pixels to 2, remainder to 1

Then calls `client.set_virtual_mask(index, w, h, mask)`. Mask dimensions always match the current hardware ROI.

### 4. `LiveResult` — new file `deapi/live_result.py`

```python
live = client.live_result(
    frame_type,           # e.g. "singleframe_integrated", "virtual_image0"
    display_fps=30,       # target display refresh rate
    window_width=None,    # optional server-side resize (pixels)
    window_height=None,
)
live.plot(ax=None)        # starts thread, returns anyplotlib figure; raises RuntimeError if called again while thread is running
live.stop()               # stops thread cleanly
```

**Thread state machine:**

```
plot() called
  └─ fetch one frame (to get shape/dtype for initial Plot2D)
  └─ start thread in IDLE mode

IDLE:   sleep(0.5) → check client.acquiring
          ↓ True
ACTIVE: get_result(window_width, window_height) → plot.set_data() → sleep(1/display_fps)
          ↓ False
IDLE:   sleep(0.5) → check client.acquiring → ...

stop() → sets threading.Event → thread exits on next sleep cycle
```

The thread detects `client.acquiring` state changes from **any source** — `client.start_acquisition()`, an external GUI, or a different API client. No explicit start signal is needed.

`window_width`/`window_height` trigger server-side resize before transmission, reducing network load at high display rates.

### 5. `client.live_result(...)` — `deapi/client.py`

Thin factory method:

```python
def live_result(self, frame_type, display_fps=30, window_width=None, window_height=None):
    from deapi.live_result import LiveResult
    return LiveResult(self, frame_type, display_fps=display_fps,
                      window_width=window_width, window_height=window_height)
```

## Composable Layout Example

```python
import anyplotlib as apl
import deapi

client = deapi.Client()
client.connect()

fig, axs = apl.subplots(1, 3)

# Interactive mask editor — push to server on drag release
client.virtual_masks[0].plot(ax=axs[0])

# Live diffraction pattern stream
client.live_result("singleframe_integrated", display_fps=30, window_width=256).plot(ax=axs[1])

# Live virtual image stream
client.live_result("virtual_image0", display_fps=30).plot(ax=axs[2])

fig  # display in Jupyter
```

## Dependencies

- `anyplotlib` added to `pyproject.toml` dependencies (installed from local path during development, PyPI once released)
- `skimage` (`scikit-image`) — already available in the project for mask geometry conversion
- `threading` — stdlib, no new dependency

## Testing

- `Result.plot()`, `VirtualMask.plot()`, `Histogram.plot()` — use `pytest-mpl` equivalent snapshot tests against anyplotlib's test utilities
- `LiveResult` thread state machine — unit test with a mock client whose `acquiring` property toggles on a timer; assert `set_data()` is called only during active mode
- `VirtualMask` widget → mask conversion — parametrized unit tests for circle, annular, polygon geometries; assert resulting numpy mask matches reference via `skimage.draw` ground truth
- Existing example scripts (`viewing_the_sensor.py`, `vdf_vbf.py`) updated to use the new API; `test_examples.py` covers them

## Migration Notes

`Result.plot()`, `VirtualMask.plot()`, and `Histogram.plot()` are breaking changes — they no longer return matplotlib axes. Existing scripts using `plt.show()` after `.plot()` will need updating. The `Examples/` directory will be updated as part of this work.
