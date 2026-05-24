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
