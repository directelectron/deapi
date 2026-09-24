"""
Imaging holes on a grid with the digital twin
=============================================

A small automation loop that drives the microscope and the camera together, the way it
would run on an instrument:

1. take a low-magnification atlas of a grid square,
2. find the holes in the holey carbon film,
3. move the stage to each hole with ``de_microscope`` (the DE-TEM-Channel client) and take
   an image at higher magnification.

Here the microscope and the camera are the `de-twin <https://github.com/directelectron/de-twin>`_
digital twin, so the example runs on any computer. Start it in a terminal first; it serves
a DE Server (deapi) on port 13250 and a DE-TEM-Channel on port 5002 for the same simulated
instrument, so stage moves change the images:

.. code-block:: bash

    pip install "deapi[twin]"
    pydeserver --port 13250 --twin --soap-port 5002 --camera DE16 --specimen "Dense Au on holey C"

Against a real instrument only the addresses change: DE-Server's port and the
DE-TEM-Channel host.

.. image:: /_static/digital_twin_holes.png
   :alt: Atlas with the holes found, and an image of each hole
"""

import time

import matplotlib.pyplot as plt
import numpy as np
from scipy import ndimage

import deapi
from de_microscope import Microscope

client = deapi.Client()
client.usingMmf = False  # the twin sends images over the socket
client.connect(port=13250)
scope = Microscope(host="127.0.0.1", port=5002)


def acquire(frames=10, fps=40):
    """One integrated, dark/gain-corrected image (like DE-MC's 'Single')."""
    client["Frames Per Second"] = fps
    client["Frame Count"] = frames
    client.start_acquisition(1)
    while client.acquiring:
        time.sleep(0.05)
    image, *_ = client.get_result("singleframe_integrated")
    return np.asarray(image, dtype=float)


def pixel_size_um():
    """Specimen pixel size reported by the server for the current magnification."""
    return client["Specimen Pixel Size X (nanometers)"] / 1000.0


# %%
# A low-magnification atlas
# -------------------------
# Spread the beam and go to low magnification so a few holes of the holey carbon fit in the
# field of view. Holes are where the beam passes through vacuum, so they are the brightest
# regions of the image.

scope["Intensity"] = 0.8
scope.set("Magnification", 2000, wait=True)
scope.set(
    "StagePosition", {"x": 40.0, "y": 0.0}, wait=True
)  # into a grid square, off the bar
start = scope["StagePosition"]
atlas = acquire()
atlas_px_um = pixel_size_um()

# %%
# Find the holes
# --------------
# Smooth, threshold the bright regions, and keep blobs of a plausible hole size
# (about 2 um across on this film) that lie wholly inside the atlas; a hole cut by the
# image edge would give a biased centre. Each hole's offset from the image centre,
# converted to micrometres, is how far the stage has to move to centre it.

smooth = ndimage.gaussian_filter(atlas, 8)
bright = smooth > np.percentile(smooth, 80)
labels, n = ndimage.label(bright)
areas = ndimage.sum(np.ones_like(atlas), labels, range(1, n + 1)) * atlas_px_um**2
centres = ndimage.center_of_mass(bright, labels, range(1, n + 1))
ny, nx = atlas.shape
margin = 1.5 / atlas_px_um  # pixels: a hole radius plus a little
holes = [
    ((c - nx / 2) * atlas_px_um, (r - ny / 2) * atlas_px_um, (r, c))
    for (r, c), a in zip(centres, areas)
    if 1.0 < a < 8.0  # um^2: about one hole
    and margin < r < ny - margin
    and margin < c < nx - margin
]
print(f"found {len(holes)} holes")

# %%
# Visit each hole
# ---------------
# Stage moves carry the specimen with them, so a feature at +dx in the image is centred by
# moving the stage by -dx. On a real column, calibrate the sign and rotation once
# (for example with ``de_microscope``'s stage calibration) and apply them here.

scope.set("Magnification", 8000, wait=True)
scope["Intensity"] = 0.6  # converge the beam again for the close-ups
hole_images = []
for dx_um, dy_um, _ in holes[:4]:
    scope.set(
        "StagePosition", {"x": start["x"] - dx_um, "y": start["y"] - dy_um}, wait=True
    )
    hole_images.append(acquire(frames=40))  # 1 s
scope.set("StagePosition", {"x": start["x"], "y": start["y"]}, wait=True)

# %%
# Plot the atlas and the holes
# ----------------------------


def show(ax, img):
    # the carbon film only dims the beam by ~25 %, while the gold particles are nearly
    # black: set the grey range from the film and the holes, not the particles
    lo, hi = np.percentile(img, [10, 99.8])
    ax.imshow(img[::4, ::4], cmap="gray", vmin=lo, vmax=hi)


fig, axes = plt.subplots(
    1, 1 + len(hole_images), figsize=(3.2 * (1 + len(hole_images)), 3.4)
)
axes = np.atleast_1d(axes)
show(axes[0], atlas)
for i, (_, _, (r, c)) in enumerate(holes[: len(hole_images)]):
    axes[0].plot(c / 4, r / 4, "o", mfc="none", mec="C1", ms=14)
    axes[0].text(c / 4, r / 4, str(i + 1), color="C1", ha="center", va="center")
axes[0].set_title("atlas, 2000x")
for i, (ax, img) in enumerate(zip(axes[1:], hole_images)):
    show(ax, img)
    ax.set_title(f"hole {i + 1}, 8000x")
for ax in axes:
    ax.axis("off")
fig.tight_layout()
plt.show()

client.disconnect()
