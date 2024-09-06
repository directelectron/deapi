import time

import numpy as np

from deapi import Client
import pytest
from deapi.data_types import PropertySpec, VirtualMask


class TestClient:
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
        client["Frames Per Second"] = 1000
        assert client["Frames Per Second"] == 1000

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
        client.scan(size_x=10, size_y=10, enable="On")
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(1)
        result = client.get_result("singleframe_integrated")
        assert isinstance(result, tuple)
        assert len(result) == 4
        assert result[0].shape == (1024, 1024)

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
        assert isinstance(client.virtual_masks[0], VirtualMask)
        assert isinstance(client.virtual_masks[0][:], np.ndarray)
        np.testing.assert_allclose(client.virtual_masks[0][:], 0)

    def test_set_virtual_mask(self, client):
        client.virtual_masks[0][:] = 1
        np.testing.assert_allclose(client.virtual_masks[0][:], 1)
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

    def test_virtual_mask_calculation(self, client):

        client.scan(size_x=10, size_y=10, enable="On")
        client.virtual_masks[2][:] = 2
        client.virtual_masks[2].calculation = "Difference"
        client.virtual_masks[2][1::2] = 0
        client.virtual_masks[2][::2] = 2
        assert client.virtual_masks[2].calculation == "Difference"
        assert client["Scan - Virtual Detector 2 Calculation"] == "Difference"
        np.testing.assert_allclose(client.virtual_masks[2][::2], 2)
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(1)
        result = client.get_result("virtual_image3")
        assert result is not None
        assert result[0].shape == (10, 10)

    def test_property_spec_set(self, client):
        client.set_property("Binning Y", 2)
        sp = client.get_property_spec("Binning Y")
        assert isinstance(sp, PropertySpec)
        assert sp.currentValue == "2"
        assert sp.options == ["1", "2", "4", "8"]
