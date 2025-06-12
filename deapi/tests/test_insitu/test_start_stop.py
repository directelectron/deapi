from codecs import ignore_errors

import pytest
import time
import os
import glob
import shutil


class TestInsitu:
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
        client["Autosave Movie"] = "On"
        client["Autosave Movie File Format"] = "MRC"
        try:
            shutil.rmtree("D:\\Temp\\start_stop")
        except FileNotFoundError:
            pass
        client["Autosave Directory"] = "D:\\Temp\\start_stop"

    @pytest.mark.server
    @pytest.mark.skip(reason="Not implemented yet")
    def test_start_stop(self, client):
        client["Frames Per Second"] = 100
        client.start_acquisition(1000)
        assert client.acquiring
        time.sleep(1)
        client.start_manual_movie_saving()
        time.sleep(1)
        client.stop_manual_movie_saving()
        time.sleep(1)
        client.stop_acquisition()
        time.sleep(3)
        assert not client.acquiring
        # autosave directory not saved
        # path = client["Autosave Movie Frames File Path"]
        path = glob.glob("D:\\Temp\\start_stop\\*movie.mrc")[0]
        assert os.path.exists(path)
        size = os.path.getsize(path)
        assert size < 2 * 1024 * 1024 * 150  # less than 150 frames
