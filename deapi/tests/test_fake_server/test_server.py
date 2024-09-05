import pytest

from deapi.simulated_server.fake_server import FakeServer


class TestFakeServer:
    @pytest.fixture
    def fake_server(self):
        return FakeServer()

    def test_parameter_values(self, fake_server):
        assert isinstance(fake_server._values, dict)

    def test_image_size(self, fake_server):
        assert fake_server["image_size_x_pixels"] == "1024"
        assert fake_server["image_size_y_pixels"] == "1024"

    def test_change_property(self, fake_server):
        fake_server["Hardware ROI Offset X"] = 512
        assert fake_server["Hardware ROI Offset X"] == "512"

    def test_get_linked_properties(self, fake_server):
        fake_server["Hardware ROI Offset X"] = 512
        assert fake_server["image_size_x_pixels"] == "512"

        fake_server["Hardware ROI Size X"] = 1024
        assert fake_server["image_size_x_pixels"] == "512"

    def test_set_virtual_image_calculation(self, fake_server):
        assert fake_server["Scan - Virtual Detector 1 Calculation"] == "Sum"
        fake_server["Scan - Virtual Detector 1 Calculation"] = "Susd"
        assert fake_server["Scan - Virtual Detector 1 Calculation"] == "Sum"

    def test_server_software_version(self, fake_server):
        assert fake_server["Server Software Version"] == "3.7.8893"
