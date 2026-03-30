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
        client.set_adaptive_roi(256, 256) # set to a reduced size for faster testing
        client["Frames Per Second"] = 100000 # set to max (will be capped by sever)
        client["Scan - Type"] = "Raster"
        # Set the software Binning to 1
        client["Binning X"] = 1
        client["Binning Y"] = 1
        client["Scan - Use DE Camera"] = "Use Frame Time"
        client["Scan - Enable"] = True
        client["Scan - Initial Delay (microseconds)"] = 0
        client["Scan - Flyback Time Going Positive (microseconds)"] = 0
        client["Scan - Flyback Time Going Negative (microseconds)"] = 0
        client["Scan - Repeats"] = 1
        client["Scan - Repeat Delay (seconds)"] = 0


    @pytest.mark.server
    def test_continual_scanning(self, client):
        """Test continual scanning logic.

        This test fails when DE-Server hasn't switched to the 4D STEM tab??? Some other
        variable needs to be set.
        """
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

        sleep(3)  # wait for any finalization

        #assert client["Frame Count"] == 8 * 8 * 3
        print("Frame Count:",client["Frame Count"])
        result = client.get_result()
        print("Aq:",result.attributes.acqIndex)


    @pytest.mark.server
    def test_sending_multiple_scan_patterns(self, client):
        """Test sending multiple scan patterns for continual scanning. It should
        properly cycle through the patterns for the specified number of repeats.
        """

        scan1 = np.array([[0, 0], [1, 0], [1, 1], [0, 1],[2, 1], [2, 0], [0,2], [1,2]] ) # 8 points)
        scans = []
        for i in range(5):
            scans.append(scan1 + 2 * i)
        client.set_xy_array(scans, height=10, width=10)

        client["Scan - Repeats"] = 100
        client["Scan - Enable"] = True
        client["Scan - Camera Frames Per Point"] = 1
        client["Scan - Repeat Delay"]
        client.start_acquisition()
        while client.acquiring:
            sleep(0.1)

        sleep(5)
        assert client["Frame Count"]- client["Actual Frames to Ignore"] *10 ==8 * 100

    @pytest.mark.server
    def test_multiple_scan_patterns_different_lengths(self, client):
        """Test sending multiple scan patterns of different lengths for continual scanning.

        Different patterns will be run depending on the index set by: `Scan - XY File Pattern ID`
        """
        scan1 = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])  # 4 points
        scan2 = np.array([[0, 0], [2, 0], [2, 2], [0, 2], [1, 1]])  # 5 points
        scan3 = np.array([[0, 0], [3, 0], [3, 3], [0, 3], [1, 1], [2, 2]])  # 6 points
        scans = [scan3, scan2, scan1]
        client.set_xy_array(scans, height=10, width=10)

        for i, num_points in enumerate([4, 5, 6]):
            client["Scan - Repeats"] = 1
            client["Scan - XY File Pattern ID"] = i
            client["Scan - Enable"] = True
            client.start_acquisition()
            while client.acquiring:
                sleep(0.1)
            print(client["Frame Count"])
            # assert client["Frame Count"] == num_points

    @pytest.mark.server
    def test_send_100_patterns(self, client):
        """Test sending 100 scan patterns.

        This is to test the stability of the system when handling a large number of patterns.
        """
        # create 1000 patterns that are 1k x 1k in size with only 10% of the points filled in.
        state = np.random.RandomState(0)
        coords = []

        for i in range(100):
            mask = np.ones((128, 128), dtype=bool)
            # randomly remove 95% of the points
            mask[state.random(mask.shape) < 0.95] = False
            # turn the mask into a list of xy coordinates
            coords.append(np.argwhere(mask))

        client.set_xy_array(coords, height=128, width=128)
        client["Scan - Repeats"] = 100
        client["Scan - Enable"] = True
        #client.start_acquisition()
        #while client.acquiring:
        #    sleep(0.1)

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


    @pytest.mark.server
    def test_saving_virtual_images(self, client, tmp_path):
        """Test that virtual images are saved correctly during continual scanning.

        This should be a 3D image with dimensions (Repeats, Size Y, Size X).
        """

        client["Scan - Size X"] = 32
        client["Scan - Size Y"] = 32
        client["Scan - Repeats"] = 2
        client["Scan - Enable"] = True
        client["Use DE Camera"] = "Use Frame Time"

        client["Autosave Directory"] =  str(tmp_path)
        client["Autosave Virtual Image 0"] = "On"

        # Start the scan
        client.start_acquisition()
        while client.acquiring:
            sleep(0.1)

        sleep(3) # wait for any finalization
        path = client["Autosave Virtual Image 0 File Path"]

        # get the file size
        osize = os.path.getsize(path)

        HEADER_SIZE = 1024  #  Header size for a MRC file
        expected_size = HEADER_SIZE + 2 * 32 * 32 * 4  # 2 repeats, 8x8 image, 4 bytes per pixel

        assert osize == expected_size

    @pytest.mark.server
    def test_frame_repeats(self,client):
        """Test that frame repeats work correctly during continual scanning.

        This should repeat each frame the specified number of times before moving to the next position.
        """
        client["Scan - Size X"] = 4
        client["Scan - Size Y"] = 4
        client["Scan - Repeats"] = 2
        client["Scan - Camera Frames Per Point"] = 8
        client["Scan - Enable"] = True
        client["Test Pattern"] = "SW Frame Number"
        client["Use DE Camera"] = "Use Frame Time"

        # Start the scan
        client.start_acquisition()
        while client.acquiring:
            sleep(0.1)

        res_1=client.get_result("virtual_image0", pixel_format="AUTO" )

        # num pixels/frame
        n_pix = client["Image Size X (pixels)"] * client["Image Size Y (pixels)"]
        print(n_pix)
        frame_number = (res_1.image / n_pix) / client["Scan - Camera Frames Per Point"]
        print(frame_number)


    @pytest.mark.server
    def test_frame_repeats_auto_save(self,client):
        """Test that frame repeats work correctly during continual scanning.

        This should repeat each frame the specified number of times before moving to the next position.
        """
        client["Scan - Size X"] = 16
        client["Scan - Size Y"] = 16
        client["Scan - Repeats"] = 1
        client["Scan - Camera Frames Per Point"] = 8
        client["Scan - Enable"] = True
        client["Test Pattern"] = "SW Frame Number"
        client["Autosave Movie"] = "On"
        client["Autosave Virtual Image 0"] = "On"
        client["Autosave 4D File Format"] = "MRC"
        client["Use DE Camera"] = "Use Frame Time"

        # Start the scan
        client.start_acquisition()
        while client.acquiring:

            sleep(0.1)
        print(client["Acquisition Status"])
        sleep(3)
        res_1=client.get_result("virtual_image0", pixel_format="AUTO" )

        # num pixels/frame
        n_pix = client["Image Size X (pixels)"] * client["Image Size Y (pixels)"]
        print(n_pix)
        frame_number = (res_1.image / n_pix) / client["Scan - Camera Frames Per Point"]
        print("frame1", frame_number)

        client["Scan - Camera Frames Per Point"] = 4
        client["Scan - Repeats"] = 3

        client.start_acquisition()
        while client.acquiring:
            sleep(0.1)
        sleep(3)
        print(client["Acquisition Status"])
        res_2=client.get_result("virtual_image0", pixel_format="AUTO" )
        frame_number_2 = (res_2.image / n_pix) / client["Scan - Camera Frames Per Point"]
        print("frame2", frame_number_2)

        # test the size of the result...

        path = client["Autosave Movie Frames File Path"]

        # get the file size
        osize = os.path.getsize(path)

        HEADER_SIZE = 1024  #  Header size for a MRC file
        image_size = client["Image Size X (pixels)"] * client["Image Size Y (pixels)"] * 2  # 4 bytes per pixel
        expected_size = HEADER_SIZE +  (image_size*
                                        client["Scan - Size X"] *
                                        client["Scan - Size Y"] *
                                        client["Scan - Repeats"])

        assert osize == expected_size

        client["Scan - Camera Frames Per Point"] = 8
        client["Scan - Repeats"] = 2

        client.start_acquisition()
        while client.acquiring:
            sleep(0.1)
        sleep(1)
        res_2 = client.get_result("virtual_image0", pixel_format="AUTO")
        frame_number_2 = (res_2.image / n_pix) / client["Scan - Camera Frames Per Point"]
        print("frame3",frame_number_2)
        # test the size of the result...

        path = client["Autosave Movie Frames File Path"]

        # get the file size
        osize = os.path.getsize(path)

        HEADER_SIZE = 1024  # Header size for a MRC file
        image_size = client["Image Size X (pixels)"] * client["Image Size Y (pixels)"] * 2  # 2 bytes per pixel
        expected_size = HEADER_SIZE + (image_size *
                                       client["Scan - Size X"] *
                                       client["Scan - Size Y"] *
                                       client["Scan - Repeats"])  # 2 bytes per pixel

        assert osize == expected_size


    @pytest.mark.parametrize("fly_back_time", [0, 1000, 4000])
    @pytest.mark.server
    def test_hidden_scan_points_single_scan(self, client,fly_back_time):
        """Test that hidden scan points are properly ignored during continual scanning.

        This should ensure that points marked as hidden are not included in the scan pattern.
        """
        size_x = 16
        size_y = 16
        client["Scan - Use DE Camera"] = "Off"
        client["Scan - Size X"] = size_x
        client["Scan - Size Y"] = size_y
        client["Scan - Dwell Time (microseconds)"] = 1000

        # Recorded Scan points  =  16 x 16 = 256
        client["Scan - Flyback Time Going Positive (microseconds)"] = fly_back_time
        client["Scan - Flyback Time Going Negative (microseconds)"] = 0
        client["Scan - Repeat Delay (seconds)"] = 0
        client["Scan - Initial Delay (microseconds)"] = 0
        fly_back_time = client["Scan - Flyback Time Going Positive (microseconds)"]
        points_per_row = np.ceil(fly_back_time/client["Scan - Dwell Time (microseconds)"])

        assert client["Scan - Flyback Time Going Positive (count)"] == points_per_row
        total_points = size_x * size_y + size_y * points_per_row
        print("Total points:", total_points)
        assert client["Scan - Points"] == total_points
        assert client["Scan - Points (Not Recorded)"] == size_y * points_per_row
        assert client["Scan - Points (Recorded)"] == size_x * size_y

    @pytest.mark.parametrize("initial_delay", [0, 1000, 5000])
    @pytest.mark.server
    def test_initial_delay(self, client, initial_delay):
        """Test that initial delay is properly applied during continual scanning.

        This should ensure that the specified initial delay is observed before the scan starts.
        """
        size_x = 16
        size_y = 16
        client["Scan - Use DE Camera"] = "Off"
        client["Scan - Size X"] = size_x
        client["Scan - Size Y"] = size_y
        client["Scan - Dwell Time (microseconds)"] = 1000
        client["Scan - Initial Delay (microseconds)"] = initial_delay

        extra_points  = np.ceil(initial_delay/client["Scan - Dwell Time (microseconds)"])
        total_points = size_x * size_y +  extra_points
        print("Total points:", total_points)
        assert client["Scan - Points"] == total_points
        assert client["Scan - Points (Not Recorded)"] == extra_points
        assert client["Scan - Points (Recorded)"] == size_x * size_y


    @pytest.mark.parametrize("initial_delay", [0, 1000, 5000])
    @pytest.mark.server
    def test_initial_delay_repeats(self, client, initial_delay):
        """Test that initial delay is properly applied during continual scanning.

        This should ensure that the specified initial delay is observed before the scan starts.
        """
        size_x = 16
        size_y = 16
        repeats = 5
        client["Scan - Use DE Camera"] = "Off"
        client["Scan - Size X"] = size_x
        client["Scan - Size Y"] = size_y
        client["Scan - Repeats"] = repeats
        client["Scan - Dwell Time (microseconds)"] = 1000
        client["Scan - Initial Delay (microseconds)"] = initial_delay

        extra_points  = np.ceil(initial_delay/client["Scan - Dwell Time (microseconds)"])
        total_points = size_x * size_y * repeats +  extra_points * repeats
        print("Total points:", total_points)
        print("Extra points:",  client["Scan - Points (Total)"]  - total_points)

        assert client["Scan - Initial Delay Count"] == extra_points # For 1 Scan

        assert client["Scan - Points"] == total_points # For all repeats
        assert client["Scan - Points (Not Recorded)"] == extra_points * repeats  # For all repeats
        assert client["Scan - Points (Recorded)"] == size_x * size_y * repeats # For all repeats

        assert client["Actual Frames to Ignore"] == extra_points * repeats

    @pytest.mark.parametrize("fly_back_time", [0, 1000, 5000])
    @pytest.mark.server
    def test_flyback_time_repeats(self, client, fly_back_time):
        """Test that flyback time is properly applied during continual scanning.

        This should ensure that the specified flyback time is observed between rows during the scan.
        """
        size_x = 16
        size_y = 16
        repeats = 5
        client["Scan - Use DE Camera"] = "Off"
        client["Scan - Size X"] = size_x
        client["Scan - Size Y"] = size_y
        client["Scan - Repeats"] = repeats
        client["Scan - Dwell Time (microseconds)"] = 1000
        client["Scan - Flyback Time (microseconds)"] = fly_back_time
        points_per_row = np.ceil(fly_back_time/client["Scan - Dwell Time (microseconds)"])
        total_points = (size_x * size_y + size_y * points_per_row) * repeats
        print("Total points:", total_points)
        assert client["Scan - Points"] == total_points
        assert client["Scan - Points (Not Recorded)"] == size_y * points_per_row * repeats
        assert client["Scan - Points (Recorded)"] == size_x * size_y * repeats

        #assert client["Actual Frames to Ignore"] == size_y * points_per_row * repeats

        assert client["Number of Frames To Grab"] == total_points