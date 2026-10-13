"""
Taking an Image every 10 seconds
================================

This example shows how to take an image every minute.  The results are saved to disk as:

- Individual frames (Movies)
- The final summed image (Final Image)

In this case we can set the "Autosave Movie Sum Count" to 10. This will sum 10 frames together
before saving the final image.
"""

from cgitb import enable

import deapi
import matplotlib.pyplot as plt
import time
import sys

c = deapi.Client()

if not sys.platform.startswith("win"):
    c.usingMmf = False  # True if on same machine as DE Server and a Windows machine

c.connect()

# Set the autosave directory
loc_time = time.localtime()
c["Autosave Directory"] = (
    f"D:\\Service\\{loc_time.tm_year}-{loc_time.tm_mon}-{loc_time.tm_mday}"
)

c["Autosave Movie"] = "On"  # Save the individual frames
c["Autosave Final Image"] = "On"  # Save the final summed image
c["Exposure Time (seconds)"] = (
    1  # The total number of frames summed for one call to `c.start_acquisition`.
)

c.scan(enable="Off")  # Make Sure we disable the scan, we are just taking images
results = []  # store the results in a list

for i in range(5):  # increase this for more images
    print(f"Taking image {i + 1} of 10")
    c.start_acquisition(
        1
    )  # Acquire one image (This is non-blocking and should run very fast)
    time.sleep(5)  # sleep for 5 seconds

    # this might take a half a second?
    # You can also just skip this and load directly from the saved files. This gets only the summed image.
    results.append(c.get_result())

# %%
# Load the final summed image
# ============================
# This will load the final summed image from the first result in the list and then
# plots both the histogram and the image.


image, dtype, attributes, histogram = results[0]  # get the first result

plt.imshow(image)

c.disconnect()
