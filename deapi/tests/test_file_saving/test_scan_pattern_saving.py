"""
This Module tests the file saving capabilities of DE Server and makes sure that

"""

import hyperspy.api as hs
import pytest
import time
import numpy as np
import os


class TestSavingScans:
    @pytest.mark.parametrize("scan_type", ["Raster", "Serpentine", "Raster Interlaced"])
    @pytest.mark.parametrize("buffer", [2, 16])
    @pytest.mark.parametrize("file_format", ["HSPY", "MRC"])
    @pytest.mark.server
    def test_save_scans(self, client, scan_type, buffer, file_format):
        if client.acquiring:
            client.stop_acquisition()
        time.sleep(1)

        i = 16
        num_pos = i * i
        if not os.path.exists("D:\Temp"):
            os.mkdir("D:\Temp")
        temp_dir = "D:\Temp"

        if scan_type == "Serpentine":
            frame_num_order = np.arange(num_pos)
            frame_num_order = frame_num_order.reshape((i, i))
            frame_num_order[1::2] = frame_num_order[1::2, ::-1]
            frame_num_order = frame_num_order.reshape(-1)

        elif scan_type == "Raster Interlaced":
            frame_num_order = np.arange(num_pos)
            frame_num_order = frame_num_order.reshape((i, i))
            skips = i // 4
            frame_num_order = np.vstack(
                [frame_num_order[i::skips] for i in range(skips)]
            )
            frame_num_order = frame_num_order.reshape(-1)
        else:  # Raster
            frame_num_order = range(num_pos)
        client["Test Pattern"] = "SW Constant 1"
        client.take_dark_reference(100)
        time.sleep(1)
        client["Image Processing - Apply Gain on Movie"] = "Off"
        client["Frames Per Second"] = 100
        client["Scan - Enable"] = "On"
        client["Scan - Size X"] = i
        client["Scan - Size Y"] = i

        time.sleep(1)
        assert client["Scan - Size X"] == i
        assert client["Scan - Size Y"] == i

        client["Autosave Movie"] = "On"
        client["Autosave 4D File Format"] = file_format
        client["Autosave Virtual Image 0"] = "On"
        client["Scan - Type"] = scan_type
        client["Grabbing - Target Buffer Size (MB)"] = buffer
        client["Grabbing - Target Buffer Size (MB)"] = buffer
        client["Image Processing - Flatfield Correction"] = "None"

        client["Autosave Directory"] = temp_dir
        client["Test Pattern"] = "SW Frame Number"
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(0.1)

        time.sleep(5)  # Wait for the file to be written to disk etc.

        if file_format == "HSPY":
            movie = hs.load(client["Autosave Movie Frames File Path"])
            frame_order = movie.data[:, :, 0, 0]
            np.testing.assert_array_equal(frame_order.reshape(-1), frame_num_order)
        else:
            print(client["Autosave Movie Frames File Path"])
            fp = client["Autosave Movie Frames File Path"]
            movie = hs.load(client["Autosave Movie Frames File Path"])
            movies = movie.data.reshape(-1, 1024, 1024)
            movies[1:] = movies[1:]
            np.testing.assert_array_equal(movies[:, 0, 0], np.arange(num_pos))


class TestSavingVirtual:
    @pytest.mark.parametrize("scan_type", ["Raster", "Serpentine", "Raster Interlaced"])
    @pytest.mark.parametrize("buffer", [2, 16])
    @pytest.mark.server
    def test_save_scans(self, client, scan_type, buffer):
        i = 8
        num_pos = i * i
        if not os.path.exists("D:\Temp"):
            os.mkdir("D:\Temp")
        temp_dir = "D:\Temp"

        if scan_type == "Serpentine":
            frame_num_order = np.arange(num_pos)
            frame_num_order = frame_num_order.reshape((i, i))
            frame_num_order[1::2] = frame_num_order[1::2, ::-1]
            frame_num_order = frame_num_order.reshape(-1)

        elif scan_type == "Raster Interlaced":
            frame_num_order = np.arange(num_pos)
            frame_num_order = frame_num_order.reshape((i, i))
            skips = i // 4
            frame_num_order = np.vstack(
                [frame_num_order[i::skips] for i in range(skips)]
            )
            frame_num_order = frame_num_order.reshape(-1)
        else:  # Raster
            frame_num_order = np.arange(num_pos)

        client["Frames Per Second"] = 100
        client["Scan - Enable"] = "On"
        client.scan["Size X"] = i
        client.scan["Size Y"] = i

        client["Autosave Movie"] = "On"
        client["Autosave 4D File Format"] = "MRC"
        client["Autosave Virtual Image 0"] = "On"
        client["Scan - Type"] = scan_type
        client["Grabbing - Target Buffer Size (MB)"] = buffer
        client["Image Processing - Flatfield Correction"] = "None"

        client["Autosave Directory"] = temp_dir
        client["Test Pattern"] = "SW Frame Number"
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(0.1)

        time.sleep(2)  # Wait for the file to be written to disk etc.
        print(client["Autosave Virtual Image 0 File Path"])
        fp = client["Autosave Virtual Image 0 File Path"]
        movie = hs.load(client["Autosave Virtual Image 0 File Path"])
        np.testing.assert_array_equal(
            movie.data.reshape(-1), frame_num_order * (1024 * 1024)
        )
