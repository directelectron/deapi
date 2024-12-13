"""

This module tests file saving and loading in Hyperspy (Rosettasciio)

This should be run before any release to make sure that the file loaders downstream
work. 
"""

import os
import time
import pytest
import hyperspy.api as hs
import glob


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

    @pytest.mark.parametrize("file_format", ["MRC", "DE5", "HSPY"])
    @pytest.mark.server
    def test_save_4DSTEM(self, client, file_format):
        if not os.path.exists("D:\Temp"):
            os.mkdir("D:\Temp")
        temp_dir = "D:\Temp"
        client["Frames Per Second"] = 100
        client["Scan - Enable"] = "On"
        client.scan["Size X"] = 8
        client.scan["Size Y"] = 8
        client["Autosave Movie"] = "On"
        client["Autosave 4D File Format"] = file_format
        client["Autosave Directory"] = temp_dir
        client
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(0.1)
        s = hs.load(client["Autosave Movie Frames File Path"])
        if file_format == "MRC":
            assert s.data.shape == (64, 1024, 1024)
        elif file_format == "DE5":
            assert s.data.shape == (1024, 1024, 8, 8)
        else:
            assert s.data.shape == (8, 8, 1024, 1024)
