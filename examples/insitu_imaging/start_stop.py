"""
Event Based Recording
=====================
This example demonstrates how to start and stop recording data from some event. This is just
a simple example using the time.sleep function to wait for 10 seconds before starting the
recording but this could be any event. For example we could start recording when the temperature
starts to ramp or when there is some change in the sample from the previous image.
"""


import deapi
import time

c = deapi.Client()
c.connect()


# Set the autosave directory
loc_time = time.localtime()
c["Autosave Directory"] = f"D:\\AutomatedInSitu\\{loc_time.tm_year}-{loc_time.tm_mon}-{loc_time.tm_mday}"

c["Autosave Movie"] = "On" # Save the individual frames
c["Autosave Final Image"] = "On" # Save the final summed image
c["Autosave Movie Sum Count"] =10 # The total number of frames summed for one call to `c.start_acquisition`.

# Usually maximum FPS and then increase Autosave Movie Sum Count to get the desired frame rate
c["Frames Per Second"] = 100

c.start_acquisition(numberOfAcquisitions=1000)

# %%
# Running Acquisition
# ===================
# This will run the acquisition for 1000 repeats at 100/10 FPS (10 FPS). In total this
# will take 100 seconds to complete. If for some reason we want to start recording midway
# through an acquisition, for example if we start applying a temperature ramp, or if the
# sample starts to change we can use the `start_manual_movie_saving` function to start recording.


time.sleep(10) # wait for 10 seconds
c.start_manual_movie_saving() # start recording
time.sleep(10) # wait for 10 seconds
c.stop_manual_movie_saving() # stop recording

while c.acquiring:
    time.sleep(1) # wait for acquisition to finish

