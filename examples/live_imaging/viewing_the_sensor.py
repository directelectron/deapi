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
"""

from deapi import Client
import matplotlib.pyplot as plt
import numpy as np

client = Client()
client.connect()  # connect to the running DE Server

client.scan(size_x=128, size_y=128, enable="On")
client.start_acquisition(1)


fig, axs = plt.subplots(1,2)
data, _,_,_= client.get_result("virtual_image0")
live_im = axs[0].imshow(np.zeros_like(data))

data2, _, _, _= client.get_result("singleframe_integrated")
live_virt_im = axs[1].imshow(np.zeros_like(data))

while client.acquiring:
    data, _,_,_ = client.get_result("singleframe_integrated")
    live_im.set_data(data)

    data, _,_,_ = client.get_result("virtual_image0")
    live_virt_im.set_data(data)
    plt.pause(.02)  # allow the matplotlib event loop to run. ~50 fps. Anything faster we need to
    # use blitting in matplotlib. (up to ~500 fps)
    live_im.autoscale()
    live_virt_im.autoscale()