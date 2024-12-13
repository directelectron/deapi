"""
This module tests file saving and loading in LiberTEM

This should be run before any release to make sure that the file loaders downstream
work.
"""

import libertem.api as lt
import pytest
import os
import glob
import time


class TestLoadingLiberTEM:
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

    @pytest.mark.parametrize(
        "file_format", ["DE5", "HSPY"]
    )  # MRC file loading in LiberTEM is broken!
    @pytest.mark.server
    def test_save_4DSTEM(self, client, file_format):
        if not os.path.exists("D:\Temp"):
            os.mkdir("D:\Temp")
        temp_dir = "D:\Temp"
        client["Frames Per Second"] = 100
        client["Scan - Enable"] = "On"
        client.scan["Size X"] = 16
        client.scan["Size Y"] = 8
        client["Autosave Movie"] = "On"
        client["Autosave Movie File Format"] = file_format
        client["Autosave Directory"] = temp_dir
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(0.1)
        movie = glob.glob(temp_dir + "/*movie." + file_format.lower())[0]
        dataset = lt.Context().load("auto", path=movie)
        assert tuple(dataset.shape) == (8, 16, 1024, 1024)
