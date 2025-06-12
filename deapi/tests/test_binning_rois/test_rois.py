import pytest
import numpy as np


class TestROIs:
    @pytest.mark.server
    @pytest.mark.parametrize("size", (1024, 512, 256, 12, 11, 7))
    def test_adaptive_roi(self, client, size):
        client.set_adaptive_roi(size_x=size, size_y=size)
        if np.log2(size) % 1 == 0:
            assert client.get_property("Hardware ROI Size X") == size
            assert client.get_property("Hardware ROI Size Y") == size
            assert client.get_property("Crop Size X") == size
            assert client.get_property("Crop Size Y") == size
            assert client.get_property("Crop Offset X") == 0
            assert client.get_property("Crop Offset Y") == 0
        else:
            assert client.get_property("Crop Size X") == size
            assert client.get_property("Crop Size Y") == size
            hw_roi_size = client.get_property("Hardware ROI Size X")
            assert client.get_property("Crop Offset X") == (hw_roi_size - size + 1) // 2
