"""
Taking an Image every 10 seconds
================================

This example shows how to take an image every minute.  The results are saved to disk as:

- Individual frames (Movies)
- The final summed image (Final Image)

In this case we can set the "Autosave Movie Sum Count" to 10. This will sum 10 frames together
before saving the final image.
"""

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
c["Autosave Movie Sum Count"] = (
    10  # The total number of frames summed for one call to `c.start_acquisition`.
)

results = []  # store the results in a list

for i in range(10):
    c.start_acquisition(
        1
    )  # Acquire one image (This is non-blocking and should run very fast)
    time.sleep(10)  # sleep for 60 seconds

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
