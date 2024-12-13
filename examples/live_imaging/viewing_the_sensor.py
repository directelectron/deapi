"""
Viewing Sensor Data During Acquisition
======================================

This example shows how to view the sensor data during acquisition. This is useful for
monitoring the data during acquisition.

This example will:

1. Connect to the DE server
2. Start an acquisition
3. Continuously update a plot of the sensor data during acquisition
4. Continually update a plot of the virtual image 0 (The sum of the sensor data) during acquisition

Note: Using the qt matplotlib backend will make the plotting update.
"""

#  %matplotlib qt
from deapi import Client
import matplotlib.pyplot as plt
import numpy as np

client = Client()
client.usingMmf = False

client.connect(port=13241)  # connect to the running DE Server
client["Frames Per Second"] = 500
client.scan(size_x=64, size_y=64, enable="On")
client.start_acquisition(1)


fig, axs = plt.subplots(1, 2)
data, _, _, _ = client.get_result("virtual_image0")
live_im = axs[0].imshow(np.zeros_like(data))

data2, _, _, _ = client.get_result("singleframe_integrated")
live_virt_im = axs[1].imshow(np.zeros_like(data))

# %%
# Plotting the Sensor Data
# ------------------------
# We will plot the sensor data during acquisition. Note that matplotlib will block unless you are
# using the Qt backend, and you won't get a live view unless you initialize the plot first and then
# update the data. If you have troubles with this please raise an issue on the github page.

while client.acquiring:
    data, _, _, _ = client.get_result("singleframe_integrated")
    live_im.set_data(data)

    data, _, _, _ = client.get_result("virtual_image0")
    live_virt_im.set_data(data)
    plt.pause(
        0.02
    )  # allow the matplotlib event loop to run. ~50 fps. Anything faster we need to
    # use blitting in matplotlib. (up to ~500 fps)
    live_im.autoscale()
    live_virt_im.autoscale()
