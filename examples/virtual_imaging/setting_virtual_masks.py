"""
Creating a Custom Virtual Mask
==============================

Virtual images are easily created from a
series of (currently) 4 seperate masks. These masks
are 8 bit images with values:


0: Negative Mask, pixel values subtracted
1: Default value, pixels not accounted for
2: Positive Mask, pixel values added


Additionally virtual images can be

"""

from deapi import Client
import matplotlib.pyplot as plt
import time
from skimage.draw import disk

c = Client()
c.usingMmf = False
c.connect(port=13241)  # connect to the running DE Server

c.virtual_masks[0][:] = 1  # Set everything to 1
c.virtual_masks[0].plot()  # plot the current v0 mask

# %%
# Changing the virtual mask
# -------------------------
# Each of the virtual masks will act like a numpy array such
# that you can use numpy fancy indexing to slice or assign
# the array. For example we can set a portion of the mask to
# be 2 (positive mask)

c.virtual_masks[0][0:25] = 2  # first 25 pixels
c.virtual_masks[0].name = "Sum Virt Img"
c.virtual_masks[0].plot()

# %%
# Subtracting and adding
# ----------------------
# Different modes can be used with each virtual image. These are set using
# The calculation attribute. Lets try that with Virtual image 1

c.virtual_masks[1].calculation = "Difference"
c.virtual_masks[1].name = "Diff Virt Img"
c.virtual_masks[1][1::2] = 0  # every other pixel subtracts
c.virtual_masks[1][::2] = 2  # every other pixel subtracts
c.virtual_masks[1].plot()

# %%
# Creating a Virtual BrightField Image
# ------------------------------------

c.virtual_masks[2].calculation = "Sum"
c.virtual_masks[2].name = "VBF"
shape = c.virtual_masks[2][:].shape
rr, cc = disk((shape[0] // 2, shape[1] // 2), 100)
c.virtual_masks[2][:] = 1
c.virtual_masks[2][rr, cc] = 2
c.virtual_masks[2].plot()

# %%

# Plotting Multiple Virtual Images
# --------------------------------
# We can also make a tableau of virtual images using the matplotlib.pyplot
# package and passing an Axis to the plot function

fig, axs = plt.subplots(1, 2)
for a, v in zip(axs, c.virtual_masks):
    v.plot(ax=a)

# %%
# Starting an Acquisition
# -----------------------
# Once we have set up an experiment we can start an acquisition using the
# start acquisition function

c["Frames Per Second"] = 5000  # 5000 frames per second
c.scan(enable="On", size_x=128, size_y=128)
c.start_acquisition()

while c.acquiring:  # wait for acquisition to finish and then plot the results
    time.sleep(1)

fig, axs = plt.subplots(1, 3)
for a, virt in zip(axs, ["virtual_image0", "virtual_image1", "virtual_image2"]):
    data, _, _, _ = c.get_result(virt)
    a.imshow(data)
