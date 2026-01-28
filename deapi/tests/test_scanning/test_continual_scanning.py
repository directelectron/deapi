"""
This class is used for testing repeated scans.  The main purpose is to ensure that
the scanning logic will properly cycle from the end of one scan to the beginning of the next
without errors.

Expected behavior:
"""
import numpy as np
import pytest
from time import sleep


class TestContinualScanning:
    """Test class for continual scanning functionality."""
    @pytest.fixture(autouse=True)
    def clean_state(self, client):
        # First set the hardware ROI to a known state
        client["Hardware ROI Offset X"] = 0
        client["Hardware ROI Offset Y"] = 0
        client["Hardware Binning X"] = 1
        client["Hardware Binning Y"] = 1
        client["Hardware ROI Size X"] = 1024
        client["Hardware ROI Size Y"] = 1024
        client["Scan - Type"] = "Raster"
        # Set the software Binning to 1
        client["Binning X"] = 1
        client["Binning Y"] = 1

    @pytest.mark.server
    def test_continual_scanning(self, client):
        """Test continual scanning logic."""
        # Set up scan parameters
        client["Scan - Size X"] = 8
        client["Scan - Size Y"] = 8
        client["Scan - Repeats"] = 3
        client["Scan - Enable"] = True

        assert client["Scan - Size X"] == 8
        assert client["Scan - Size Y"] == 8
        assert client["Scan - Repeats"] == 3
        assert client["Scan - Enable"] == "On"

        # Start the scan
        client.start_acquisition()
        while client.acquiring:
            sleep(0.1)
        # After scan completion, verify the scan parameters

        assert client["Frame Count"] == 8*8*3

    @pytest.mark.server
    def test_sending_multiple_scan_patterns(self, client):

        scan1 = np.array([[0,0],[1,0],[1,1],[0,1]])
        scans = []
        for i in range(10):
            scans.append(scan1 + 2*i)
        client.set_xy_array(scans, height=40, width=40)

        #client["Scan - Repeats"] = 100
        #client["Scan - Enable"] = True
        #client.start_acquisition()

        #client.set_adaptive_roi(128,128)