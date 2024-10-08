"""
Setting up a STEM Experiment
=============================
This script demonstrates how to set up a STEM experiment using the DE API.

This script will:
1. Connect to the DE server
2. Set the hardware ROI to 256x256
3. Set the scan size to 256x256
4. Set the number of frames per second to 1000
5. Acquire a STEM image using a HAADF detector
"""

from deapi import Client

# %%
# Connect to the DE server
client = Client()
client.usingMmf = False
client.connect(port=13241)  # connect to the running DE Server

# %%
# Set the hardware ROI to 256x256
# --------------------------------
# In this case we just use the center 256 pixels of the 1024 pixel sensor.

client["Hardware ROI Size X"] = 256
client["Hardware ROI Size Y"] = 256
client["Hardware ROI Offset X"] = 256
client["Hardware ROI Offset Y"] = 256

# %%
# Set the scan size to 256x256
client.scan(size_x=256, size_y=256, enable="On")

# %%
# Set the number of frames per second to 1000
client["Frames Per Second"] = 1000


# %%
# Acquire a STEM image using a HAADF detector
