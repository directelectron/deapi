"""
This class is used for testing repeated scans.  The main purpose is to ensure that
the scanning logic will properly cycle from the end of one scan to the beginning of the next
without errors.

Expected behavior:
"""
import os

import numpy as np
import pytest
from time import sleep
import glob

class TestContinualScanning:
    """Test class for continual scanning functionality."""

    @pytest.fixture
    def tmp_path(self):
        import tempfile
        from pathlib import Path
        temp_dir = Path("D:/temp") / f"test_{id(self)}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        yield temp_dir
        # Optional: cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture(autouse=True)
    def clean_state(self, client):
        # First set the hardware ROI to a known state
        client["Hardware Binning X"] = 1
        client["Hardware Binning Y"] = 1
        client.set_adaptive_roi(size=(256, 256)) # set to a reduced size for faster testing
        client["Frames Per Second"] = 100000 # set to max (will be capped by sever)
        client["Scan - Type"] = "Raster"
        # Set the software Binning to 1
        client["Binning X"] = 1
        client["Binning Y"] = 1
        client["Scan - Use DE Camera"] = "On"

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

        assert client["Frame Count"] == 8 * 8 * 3

    @pytest.mark.server
    def test_sending_multiple_scan_patterns(self, client):
        """Test sending multiple scan patterns for continual scanning. It should
        properly cycle through the patterns for the specified number of repeats.
        """

        scan1 = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
        scans = []
        for i in range(10):
            scans.append(scan1 + 2 * i)
        client.set_xy_array(scans, height=40, width=40)

        client["Scan - Repeats"] = 100
        client["Scan - Enable"] = True
        client.start_acquisition()
        while client.acquiring:
            sleep(0.1)
        assert client["Frame Count"] == 4 * 100

    @pytest.mark.server
    def test_multiple_scan_patterns_different_lengths(self, client):
        """Test sending multiple scan patterns of different lengths for continual scanning.

        Different patterns will be run depending on the index set by: `Scan - XY File Pattern ID`
        """
        scan1 = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])  # 4 points
        scan2 = np.array([[0, 0], [2, 0], [2, 2], [0, 2], [1, 1]])  # 5 points
        scan3 = np.array([[0, 0], [3, 0], [3, 3], [0, 3], [1, 1], [2, 2]])  # 6 points
        scans = [scan1, scan2, scan3]
        client.set_xy_array(scans, height=10, width=10)

        for i, num_points in enumerate([2, 3, 4]):
            client["Scan - Repeats"] = 1
            client["Scan - XY File Pattern ID"] = i
            client["Scan - Enable"] = True
            client.start_acquisition()
            while client.acquiring:
                sleep(0.1)
            assert client["Frame Count"] == num_points

    @pytest.mark.server
    def test_repeat_scanning_no_DE_camera(self, client):
        """Test continual scanning without using the DE camera.

        This is to test only using an EXT detector and not the DE camera.
        """

        client["Scan - Size X"] = 5
        client["Scan - Size Y"] = 5
        client["Scan - Repeats"] = 10
        client["Scan - Enable"] = True
        client["Scan - Use DE Camera"] = "Off"

        # Start the scan
        client.start_acquisition()
        while client.acquiring:
            sleep(0.1)
        # After scan completion, verify the scan parameters

        result = client.get_result("external_image1")

        assert result.attributes.acq_index == 49  # 5x5x10 - 1 = 49

    @pytest.mark.server
    def test_saving_virtual_images(self, client, tmp_path):
        """Test that virtual images are saved correctly during continual scanning.

        This should be a 3D image with dimensions (Repeats, Size Y, Size X).
        """

        client["Scan - Size X"] = 4
        client["Scan - Size Y"] = 4
        client["Scan - Repeats"] = 2
        client["Scan - Enable"] = True
        client["Virtual Image 0 - Save To File"] = "On"

        client["Autosave Directory"] =  str(tmp_path)
        client["Autosave Virtual Image 0"] = "On"

        # Start the scan
        client.start_acquisition()
        while client.acquiring:
            sleep(0.1)

        path = client["Autosave Virtual Image 0 File Path"]

        assert path.startswith(str(tmp_path))

        # get the file size
        osize = os.path.getsize(path)

        HEADER_SIZE = 1024  #  Header size for a MRC file
        expected_size = HEADER_SIZE + 2 * 4 * 4  # 2 repeats, 4x4 image, 4 bytes per pixel

        assert osize == expected_size
