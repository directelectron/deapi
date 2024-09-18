import time
import pytest

class TestFPS01:
    """
    Test the Frames Per Second property. Make sure that it is set to the
    maximum value and that the camera is able to acquire at that size.
    """
    @pytest.fixture(autouse=True)
    def clean_state(self, client):
        # First set the hardware ROI to a known state
        client["Hardware ROI Offset X"] = 0
        client["Hardware ROI Offset Y"] = 0
        client["Hardware Binning X"] = 1
        client["Hardware Binning Y"] = 1
        client["Hardware ROI Size X"] = 1024
        client["Hardware ROI Size Y"] = 1024
        # Set the software Binning to 1
        client["Binning X"] = 1
        client["Binning Y"] = 1


    @pytest.mark.parametrize("fps", [25, 50])
    @pytest.mark.server
    def test_set_fps(self,client, fps):
        deClient = client
        deClient.SetProperty('Frames Per Second', fps)
        value = deClient.GetProperty('Frames Per Second')
        assert value == fps

    @pytest.mark.server
    def test_max_fps(self,client):
        deClient = client
        max_fps = deClient.GetProperty('Frames Per Second (Max)')
        deClient.SetProperty('Frames Per Second', max_fps*2)
        value = deClient.GetProperty('Frames Per Second')
        assert value == max_fps
    """
    @pytest.mark.parametrize("fps", [100, 200])
    @pytest.mark.parametrize("exposure", [5,1])
    @pytest.mark.server
    def test_frame_count(self, client, fps, exposure):
        deClient = client
        deClient.SetProperty('Frames Per Second', fps)
        deClient.SetProperty('Exposure Time (seconds)', exposure)
        frameCount = deClient.GetProperty('Frame Count')
        assert frameCount == fps * exposure
    """

class


class TestReferences07:
    @pytest.mark.server
    def test_dark_reference(self, client):
        deClient = client
        deClient.SetProperty("Autosave Crude Frames", "Off")
        deClient.SetProperty("Autosave Movie", "Off")
        deClient.SetProperty("Autosave Final Image", "Off")
        deClient.SetProperty("Image Processing - Bad Pixel Correction", "False")

        deClient.SetProperty("Log Level", "Debug")
        deClient.SetProperty("Autosave Debug Frames", "Save")
        deClient.SetProperty("Exposure Mode", "Dark")
        deClient.SetProperty("Frames Per Second", 10)

        deClient.Grab(2)

        deClient.TakeDarkReference(15)
        assert deClient.GetProperty("Reference - Dark")[:5] == "Valid"

    @pytest.mark.server
    def test_dark_reference2(self, client):
        deClient = client
        acquisitions = 10
        deClient.SetProperty('Exposure Mode', 'Dark')
        deClient.SetProperty('Frames Per Second', 10)
        deClient.SetProperty('Exposure Time (seconds)', 1)
        deClient.StartAcquisition(acquisitions)

        # Can we test to make sure the camera shutter is closed?
        while deClient.acquiring:
            time.sleep(.1)
        darkReference = deClient.GetProperty("Reference - Dark")
        return darkReference[:5] == 'Valid'

    @pytest.mark.server
    def test_gain_reference2(self, client):
        deClient = client
        acquisitions = 10
        deClient.SetProperty('Exposure Mode', 'Gain')
        deClient.SetProperty('Frames Per Second', 10)
        deClient.SetProperty('Exposure Time (seconds)', 1)
        deClient.StartAcquisition(acquisitions)

        while deClient.acquiring:
            time.sleep(.1)
        gain_reference = deClient.GetProperty("Reference - Gain")
        return gain_reference[:5] == 'Valid'
