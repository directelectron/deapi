"""
Viewing the Sensor in TEM Mode
==============================
This example shows how to view the sensor in TEM mode using the DEAPI.
"""

import deapi
from deapi.data_types import Attributes, ContrastStretchType
import time
import sys

c = deapi.Client()

if not sys.platform.startswith("win"):
    c.usingMmf = False  # True if on same machine as DE Server and a Windows machine

c.connect()

# Set the autosave directory
loc_time = time.localtime()
c["Autosave Directory"] = (
    f"D:\\Insitu\\{loc_time.tm_year}-{loc_time.tm_mon}-{loc_time.tm_mday}"
)

c["Autosave Movie"] = "On"  # Save the individual frames
c["Autosave Final Image"] = "On"  # Save the final summed image

sum_frames = 10
c["Autosave Movie Sum Count"] = (
    sum_frames  # The total number of frames summed `c.start_acquisition`.
)

c["Frames Per Second"] = 200  # The number of frames per second to acquire
c["Frame Count"] = 40  # The number of frames to acquire

print(
    f"Summed Frames Per Second: {c['Frames Per Second']/c['Autosave Movie Sum Count']}\n"
    f" Total Frames ({c['Frame Count'] / c['Autosave Movie Sum Count']})"
)

c.start_acquisition(1)  # Acquire 500 frames

#  While the acquisition is running, we can continuously poll the result

# You can also pass an Attributes object to the get_result method
# which will stretch the image to a specific size or adjust the LUT etc.
# this isn't recommended but might be useful for display purposes.

# attributes = Attributes()
# attributes.stretchType = ContrastStretchType.NATURAL
# attributes.windowWidth = c.image_sizex * 2  # 2x larger image
# attributes.windowHeight = c.image_sizey * 2  # 2x larger image

while c.acquiring:
    image, pixelFormat, attributes, histogram = c.get_result(
        frameType="singleframe_integrated",
        # atributes=attributes,
    )
    # Do something with the image
    print(f"Frame Index: {(attributes.imageIndex+1)//sum_frames}")
    print(f"Max intensity: {image.max()}")
