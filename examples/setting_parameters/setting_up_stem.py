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

from deapi.fake_client import FakeClient as Client
# from deapi import Client

# %%
# Connect to the DE server
client = Client()
client.connect()

# %%
# Set the hardware ROI to 256x256
#client.set_hw_roi(0, 0, 256, 256)

# %%
# Set the scan size to 256x256
client.scan(size_x=256, size_y=256, enable=True)

# %%
# Set the number of frames per second to 1000
client["Frames Per Second"] = 1000
client

# %%
# Acquire a STEM image using a HAADF detector
#client.start_acquisition(numberOfAcquisitions=1)



