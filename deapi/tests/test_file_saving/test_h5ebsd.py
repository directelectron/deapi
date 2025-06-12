"""

This module tests file saving for h5EBSD files


This should be run before any release to make sure that the file loaders downstream
work.
"""

import os
import time
import pytest
import h5py


class TestSavingHyperSpy:
    @pytest.fixture(autouse=True)
    def clean_state(self, client):
        # First set the hardware ROI to a known state
        client["Hardware ROI Offset X"] = 0
        client["Hardware ROI Offset Y"] = 0
        client["Hardware Binning X"] = 1
        client["Hardware Binning Y"] = 1
        client["Hardware ROI Size X"] = 1024
        client["Hardware ROI Size Y"] = 1024
        # Set the software Binning to 1
        client["Binning X"] = 1
        client["Binning Y"] = 1

    @pytest.mark.server
    def test_save_hspy_4DSTEM(self, client):
        if not os.path.exists("D:\Temp"):
            os.mkdir("D:\Temp")
        if not os.path.exists("D:\Temp\HSPY"):
            os.mkdir("D:\Temp\HSPY")
        temp_dir = "D:\Temp\HSPY"
        client["Frames Per Second"] = 100
        client["Scan - Enable"] = "On"
        client.scan["Size X"] = 8
        client.scan["Size Y"] = 8
        client["Autosave Movie"] = "On"
        client["Autosave 4D File Format"] = "HSPY"
        client["Autosave Directory"] = temp_dir
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(0.1)
        time.sleep(2)
        assert os.path.exists(client["Autosave Movie Frames File Path"])
        print(client["Autosave Movie Frames File Path"])
        h5py.File(client["Autosave Movie Frames File Path"], "r")
