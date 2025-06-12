"""
Taking a Dark Reference Image
=============================

This example shows how to take a dark reference image using the DEAPI.  For best results the dark reference should
be taken with the beam blanked and the detector shutter closed (if applicable).

For the Apollo Camera, this example is not relevant as the dark reference is automatically subtracted by the FPGA,
only a gain reference is needed.
"""

from deapi import Client
import matplotlib.pyplot as plt

client = Client()
client.connect(port=13240)  # connect to the running DE Server

# %%
# Set the acquisition parameters
# ==============================
# In most cases dark reference is taken with the same ROI/ FPS as the actual acquisition. This helps to ensure
# that dark reference accurately represents the noise in the detector during acquisition.

#client.set_adaptive_roi(size_x= 256,
#                        size_y= 256)  # Set the ROI  (this function automatically centers the ROI)

# %%
# Take the dark reference
# =======================
# This function should automatically blank the beam and close the shutter (if applicable)
# before taking the dark reference image. This function is blocking and will wait until the
# dark reference is completed.

client.take_dark_reference(frame_rate = 40, # FPS
                           )

# Get the dark reference image
image, pixel_format, attributes, histogram = client.get_result("sumtotal")

plt.imshow(image, cmap="gray")
plt.title("Dark Reference Image")

