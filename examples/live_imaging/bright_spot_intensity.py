"""
Monitoring Bright Spot Intensity
================================

This example demonstrates how to monitor the intensity of the brightest pixel in the sensor data during acquisition.
"""

import deapi
import time
import sys


client = deapi.Client()

if not sys.platform.startswith("win"):
    client.usingMmf = (
        False  # True if on same machine as DE Server and a Windows machine
    )
client.connect()

# %%
# Set the hardware ROI to 256x256
# --------------------------------
# In this case we just use the center 256 pixels of the 1024 pixel sensor. (This should be simplified in the future
# to have default values for the hardware ROI)

client["Hardware ROI Size X"] = 256
client["Hardware ROI Size Y"] = 256
client["Hardware ROI Offset X"] = 384
client["Hardware ROI Offset Y"] = 384


# Set up a 4DSTEM acquisition
# ---------------------------
# We will set up a 4DSTEM acquisition with a 64x64 scan size and 100 frames per second.
# %%
client.scan(size_x=16, size_y=16, enable="On", points_per_camera_frame=10)


# %%
# Start the acquisition
# ---------------------
# We will start the acquisition

client.start_acquisition(1)


# %%
# Monitor the intensity of the brightest pixel
# --------------------------------------------
# We will monitor the intensity of the brightest pixel in the sensor data during acquisition. This will
# not get every frame, but will get the most recent frame every 0.1 seconds after integrating the number
# of `points_per_camera_frame`.  The `histogram` is also returned which gives the data separated into
# 256 bins.

while client.acquiring:
    image, pixelFormat, attributes, histogram = client.get_result(
        "singleframe_integrated"
    )
    print(f"Max intensity: {image.max()}")
    print("Acquiring...")

time.sleep(4)

# %%
# Retract the Camera
# ------------------


client["Camera Position Control"] = "Retract"
client.disconnect()
