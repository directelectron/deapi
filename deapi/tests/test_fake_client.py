
from deapi.fake_client import FakeClient

import pytest

class TestClient:

    @pytest.fixture
    def client(self):
        c = FakeClient()
        c.connect()
        return c

    def test_client_connection(self, client):
        assert client.connected

    def test_get_property(self, client):
        assert client.get_property("Scan - Size X") == 128

    def test_set_property(self, client):
        client.set_property("Scan - Size X", 256)
        assert client.get_property("Scan - Size X") == 256

    def test_str(self, client):
        assert str(client) == "Client(host=test, port=12345, camera=Fake Test Camera)"

    def test_list_cameras(self, client):
        assert client.list_cameras() == ["Fake Test Camera"]

    def test_get_current_camera(self, client):
        assert client.get_current_camera() == "Fake Test Camera"

    def test_set_current_camera(self, client):
        client.set_current_camera("Fake Test Camera")
        assert client.get_current_camera() == "Fake Test Camera"

    def test_list_properties(self, client):
        list = client.list_properties()
        assert "Scan - Size X" in list

    def test_get_all_properties(self, client):
        properties = client.get_property_spec("Scan - Size X")

    def test_attributes(self, client):
        client.scan["size_x"] = 450
        assert client.scan["size_x"] == 450
        assert client.get_property("Scan - Size X") == 450
        client.scan["Size X"] = 128

    def test_set_multiple_attributes(self, client):
        client.scan(size_x=45, size_y=450)
        assert client.scan["size_x"] == 45
        assert client.scan["size_y"] == 450

