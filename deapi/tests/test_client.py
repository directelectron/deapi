from deapi import Client
import pytest
from deapi.data_types import PropertySpec

class TestClient:

    @pytest.fixture
    def client(self):
        c = Client()
        c.connect()
        return c

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

    def test_get_property_spec(self, client):
        properties = client.list_properties()
        spec = client.get_property_spec(properties[0])
        assert isinstance(spec, PropertySpec)



        
        








    

        
    

