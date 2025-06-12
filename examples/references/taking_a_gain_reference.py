"""
Taking a gain reference
=======================

Taking a gain reference is very similar to the steps for taking a dark reference. The main difference is
that a gain reference requires a flat field illumination.  Ideally, this illumination is similar to the
illumination used for data acquisition.

For the DE Apollo, as it is always running in counting mode, you don't have to specify that the gain reference
is counting vs integrating.  For all other detectors if you want a counting gain reference you need to
specify that the gain reference is counting and adjust the exposure accordingly so that less than 5% of
pixels are illuminated.
"""

from deapi import Client
import time
import numpy as np

client = Client()
if not client.usingMmf:
    client.usingMmf = False  # True if on same machine as DE Server and a Windows machine
client.connect(port=13240)  # connect to the running DE Server


# For the DE Apollo the Frame Rage is always 60 fps
eppixps, n_acq, sat_warn, to_warning = client.take_trial_gain_reference(frame_rate=100,
                                                                         target_electrons_per_pixel=5000,
                                                                         timeout=600,
                                                                         counting=False)

# %%
# The `take_trial_gain_reference` method will return the number of electrons per pixel per second
# the number of acquisitions needed to reach the target number of electrons per pixel, if the detector is saturated
# and a warning that the signal is too low, and it will take more than the timeout to reach the target. This method
# is also run before the client.take_gain_reference() method so if you are confident in the illumination you can
# skip this step and just run the client.take_gain_reference() method.

client.take_gain_reference(frame_rate=100,
                           target_electrons_per_pixel=5000,
                           timeout=600,
                           counting=False)
