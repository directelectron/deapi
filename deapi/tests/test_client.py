import time

import numpy as np

from deapi import Client, Histogram
import pytest
from deapi.data_types import (
    PropertySpec,
    VirtualMask,
    MovieBufferStatus,
    ContrastStretchType,
)


class TestClient:

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

    def teardown(self):
        time.sleep(0.1)

    def test_client_connection(self, client):
        assert client.connected

    def test_list_cameras(self, client):
        cameras = client.list_cameras()
        assert isinstance(cameras, list)

    def test_set_current_camera(self, client):
        cameras = client.list_cameras()
        client.set_current_camera(cameras[0])
        assert client.get_current_camera() == cameras[0]

    def test_list_properties(self, client):
        properties = client.list_properties()
        assert isinstance(properties, list)
        print(properties)

    def test_get_property(self, client):
        properties = client.list_properties()
        prop = client.get_property("Frames Per Second")
        assert isinstance(prop, float)

    def test_set_property(self, client):
        client["Frames Per Second"] = 5
        assert client["Frames Per Second"] == 5

    def test_enable_scan(self, client):
        client["Scan - Enable"] = "On"
        assert client["Scan - Enable"] == "On"

    def test_start_acquisition(self, client):
        client["Frames Per Second"] = 1000
        client.scan(size_x=10, size_y=10, enable="On")
        client.start_acquisition(1)
        assert client.acquiring
        while client.acquiring:
            time.sleep(1)
        assert not client.acquiring

    def test_start_acquisition_scan_disabled(self, client):
        client["Frames Per Second"] = 1000
        client.scan(enable="Off")
        client.start_acquisition(10)
        assert client.acquiring
        while client.acquiring:
            time.sleep(1)
        assert not client.acquiring

    def test_get_result(self, client):
        client["Frames Per Second"] = 1000
        client.scan(size_x=3, size_y=3, enable="On")
        assert client["Hardware ROI Size X"] == 1024
        assert client["Hardware ROI Size Y"] == 1024
        assert client["Hardware Binning X"] == 1
        assert client["Hardware Binning Y"] == 1
        assert client["Hardware ROI Offset X"] == 0
        assert client["Hardware ROI Offset Y"] == 0
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(1)
        result = client.get_result()
        assert isinstance(result, tuple)
        assert len(result) == 4
        assert result[0].shape == (1024, 1024)
        assert result[2].stretchType == ContrastStretchType.NONE

    @pytest.mark.server
    def test_get_histogram(self, client):
        client["Frames Per Second"] = 1000
        client.scan(size_x=10, size_y=10, enable="On")
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(1)
        result = client.get_result("singleframe_integrated")
        assert isinstance(result[3], Histogram)
        result[3].plot()

    def test_get_result_no_scan(self, client):
        client["Frames Per Second"] = 1000
        client.scan(enable="Off")
        client.start_acquisition(1)
        result = client.get_result("singleframe_integrated")
        assert isinstance(result, tuple)
        assert len(result) == 4
        assert result[0].shape == (1024, 1024)
        while client.acquiring:
            time.sleep(1)

    def test_binning_linked_parameters(self, client):

        client["Hardware Binning X"] = 2
        assert client["Hardware Binning X"] == 2
        assert client["Image Size X (pixels)"] == 512
        client.update_image_size()
        assert client.image_sizex == 512

    @pytest.mark.parametrize("binx", [1, 2])
    def test_binning(self, client, binx):
        client["Hardware Binning X"] = binx
        assert client["Hardware Binning X"] == binx
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(1)
        result = client.get_result("singleframe_integrated")
        assert result[0].shape[1] == 1024 // binx

    def test_get_virtual_mask(self, client):
        client.virtual_masks[1][:] = 1
        assert isinstance(client.virtual_masks[1], VirtualMask)
        assert isinstance(client.virtual_masks[1][:], np.ndarray)
        np.testing.assert_allclose(client.virtual_masks[1][:], 1)

    def test_set_virtual_mask(self, client):
        # client.virtual_masks[0][:] = 1
        # np.testing.assert_allclose(client.virtual_masks[0][:], 1)
        client.virtual_masks[1][:] = 1
        np.testing.assert_allclose(client.virtual_masks[1][:], 1)
        client.virtual_masks[2][:] = 2
        np.testing.assert_allclose(client.virtual_masks[2][:], 2)

    def test_resize_virtual_mask(self, client):
        client.virtual_masks[2][:] = 2
        client["Hardware ROI Offset X"] = 512
        client["Hardware ROI Offset Y"] = 512
        client["Hardware Binning X"] = 1
        client["Hardware Binning Y"] = 1
        assert client.virtual_masks[2][:].shape == (512, 512)

    def test_virtual_mask_calculation_1(self, client):
        client.virtual_masks[1].calculation = "Sum"
        client.virtual_masks[1].name = "VBF"
        client.virtual_masks[1][:] = 1  # Set to 1
        client.virtual_masks[1][10:20, :] = 2  # Set mask to 2

    def test_virtual_mask_calculation(self, client):
        client["Scan - Size X"] = 8
        client["Scan - Size Y"] = 10
        client["Scan - Type"] = "Raster"
        client["Scan - Enable"] = "On"
        assert client["Scan - Type"] == "Raster"
        assert client["Scan - Enable"] == "On"
        assert client["Scan - Size X"] == 8
        assert client["Scan - Size Y"] == 10
        client.virtual_masks[2][:] = 2
        client.virtual_masks[2].calculation = "Difference"
        client.virtual_masks[2][1::2] = 0
        client.virtual_masks[2][::2] = 2
        assert client.virtual_masks[2].calculation == "Difference"
        assert client["Scan - Virtual Detector 3 Calculation"] == "Difference"
        np.testing.assert_allclose(client.virtual_masks[2][::2], 2)
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(1)
        result = client.get_result("virtual_image3")
        assert result is not None
        assert result[0].shape == (10, 8)

    @pytest.mark.server
    def test_bin_property_set(self, client):
        client.set_property("Scan - Enable", "Off")
        client.set_property("Binning Y", 16)
        sp = client.get_property("Binning Y")
        assert sp == 16

    @pytest.mark.server
    @pytest.mark.parametrize("bin_sw", [1, 2, 4])
    def test_property_spec_set(self, client, bin_sw):
        client.set_property("Hardware Binning Y", 1)
        client.set_property("Binning Y", bin_sw)
        sp = client.get_property_spec("Binning Y")
        assert isinstance(sp, PropertySpec)
        assert sp.currentValue == str(bin_sw)
        assert (
            sp.options
            == "'1*', '2', '4', '8', '16', '32', '64', '128', '256', '512', '1024'"
        )
        client.set_property("Hardware Binning Y", 2)
        sp = client.get_property_spec("Binning Y")
        assert sp.currentValue == str(bin_sw)
        assert (
            sp.options == "'1*', '2', '4', '8', '16', '32', '64', '128', '256', '512'"
        )

    @pytest.mark.parametrize("bin", [1, 2])
    @pytest.mark.parametrize("offsetx", [0, 512])
    @pytest.mark.parametrize("size", [512, 256])
    @pytest.mark.parametrize("bin_sw", [1, 2, 4])
    def test_image_size(self, client, bin, offsetx, size, bin_sw):
        client["Hardware ROI Offset X"] = 0
        client["Hardware ROI Offset Y"] = 0
        client["Hardware ROI Size X"] = 1024
        client["Hardware ROI Size Y"] = 1024
        client["Hardware Binning X"] = 1
        client["Hardware Binning Y"] = 1
        client["Binning X"] = 1
        client["Binning Y"] = 1
        client["Crop Offset X"] = 0
        client["Crop Offset Y"] = 0

        assert client["Image Size X (pixels)"] == 1024
        assert client["Image Size Y (pixels)"] == 1024

        client["Hardware Binning X"] = bin
        client["Hardware Binning Y"] = bin
        assert client["Hardware Binning X"] == bin
        assert client["Hardware Binning Y"] == bin
        assert client["Image Size X (pixels)"] == 1024 // bin
        assert client["Image Size Y (pixels)"] == 1024 // bin

        client["Hardware ROI Offset X"] = offsetx
        assert client["Hardware ROI Offset X"] == offsetx
        assert client["Image Size X (pixels)"] == (1024 - offsetx) // bin

        client["Hardware ROI Size X"] = size
        assert client["Hardware ROI Size X"] == size
        assert client["Image Size X (pixels)"] == size // bin

        client["Binning X"] = bin_sw
        client["Binning Y"] = bin_sw
        assert client["Binning X"] == bin_sw
        assert client["Image Size X (pixels)"] == size // bin_sw // bin

    def test_stream_data(self, client):
        client["Frames Per Second"] = 5
        client.scan(size_x=10, size_y=10, enable="On")
        client.start_acquisition(1, requestMovieBuffer=True)
        numberFrames = 0
        index = 0
        status = MovieBufferStatus.OK
        success = True
        info, buffer, total_bytes, numpy_dtype = client.current_movie_buffer()
        number_frames = 0
        while status == MovieBufferStatus.OK and success:
            status, total_bytes, number_frames, buffer = client.GetMovieBuffer(
                buffer, total_bytes, number_frames
            )

            ## CovertToImage(movieBuffer, headerBytes, dataType, imageW, imageH, numberFrames);
            frameIndexArray = np.frombuffer(
                buffer, np.longlong, offset=0, count=numberFrames
            )
            movieBuffer = np.frombuffer(
                buffer,
                dtype=numpy_dtype,
                offset=info.headerBytes,
                count=info.imageH * info.imageW * numberFrames,
            )

            ## Verify the value

            for i in range(numberFrames):
                # Calculate the starting index for each 64-bit integer (8 bytes per integer)
                start_index = i * 8

                # Extract the 64-bit integer frameIndex using struct.unpack
                frame_index = frameIndexArray[i]

                # Extract the first pixel value
                first_pixel_value = movieBuffer[i * info.imageW * info.imageH]

                success = (
                    success and (frame_index == index) and (first_pixel_value == index)
                )

                index += 1
                if not success:
                    break
        time.sleep(4)

    @pytest.mark.server
    def test_set_xy_array(self, client):
        client["Scan - Type"] = "Raster"
        client["Scan - Enable"] = "On"
        mask = np.ones((12, 12))
        mask[3:-3, 3:-3] = 0
        pos = np.argwhere(mask)

        is_set = client.set_xy_array(pos)
        assert client["Scan - Type"] == "XY Array"
        assert is_set
        assert client["Scan - Points"] == np.sum(mask)

        pos2 = np.vstack([pos, pos])
        is_set = client.set_xy_array(pos2)
        assert is_set
        assert client["Scan - Points"] == np.sum(mask) * 2
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(1)
        result = client.get_result("virtual_image1")
        assert result[0].shape == (12, 12)
        client["Scan - Type"] = "Raster"  # clean up

    @pytest.mark.server
    def test_gain_reference(self, client):
        client["Test Pattern"] = "SW Constant 400"
        client.TakeDarkReference(100)  # take a dark reference first with 400 ADU
        client["Test Pattern"] = "SW Constant 1600"
        client.take_gain_reference(100, target_electrons_per_pixel=1000, counting=False)

    @pytest.mark.server
    def test_gain_reference_too_bright(self, client):
        client["Test Pattern"] = "SW Constant 1"
        client.TakeDarkReference(100)  # take a dark reference first with 400 ADU
        client["Test Pattern"] = "SW Gaussian M1600 D200"

        with pytest.raises(ValueError):
            client.take_gain_reference(
                100, target_electrons_per_pixel=1000, counting=False
            )

    @pytest.mark.server
    def test_get_trial_gain_reference(self, client):
        client["Scan - Enable"] = "Off"
        client["Test Pattern"] = "SW Constant 400"
        client.take_dark_reference(10)  # take a dark reference first with 400 ADU
        client["Test Pattern"] = "SW Constant 1600"  # others don't work??
        exposure, num_acquire, el = client.take_trial_gain_reference(10)
        assert exposure == 1
        assert el > 0

    @pytest.mark.server
    def test_flip_dark_reference(self, client):
        """Test to make sure that the dark reference is still correct after flipping."""
        client["Scan - Enable"] = "Off"
        client["Test Pattern"] = "SW Gradient Diagonal"
        client["Frames Per Second"] = 10
        client.take_dark_reference(frame_rate=10)
        client["Image Processing - Flatfield Correction"] = "Dark"
        client.start_acquisition(1)
        # assert that the dark reference corrects the image to zero...
        while client.acquiring:
            time.sleep(1)
        image = client.get_result()[0]
        np.testing.assert_array_equal(image, 0)

        # Now flip the dark reference
        client["Image Processing - Flip Horizontally"] = "On"
        client["Exposure Time (seconds)"] = 1
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(1)
        image = client.get_result()[0]
        np.testing.assert_array_equal(image, 0)
        client["Image Processing - Flip Horizontally"] = "Off"

        # test bin by a factor of 2

        client["Binning X"] = 2
        client["Binning Y"] = 2
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(1)
        image = client.get_result()[0]
        np.testing.assert_array_equal(image, 0)
