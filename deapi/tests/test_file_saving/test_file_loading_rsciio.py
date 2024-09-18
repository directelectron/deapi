"""

This module tests file saving and loading in Hyperspy (Rosettasciio)

This should be run before any release to make sure that the file loaders downstream
work. 
"""


import os
import time
import pytest
import hyperspy.api as hs
import glob


class TestSavingHyperSpy:

    @pytest.mark.parametrize("file_format", ["MRC", "DE5", "HSPY"])
    @pytest.mark.server
    def test_save_4DSTEM(self, client, file_format):
        if not os.path.exists("D:\Temp"):
            os.mkdir("D:\Temp")
        temp_dir = "D:\Temp"
        client["Frames Per Second"] = 100
        client["Scan - Enable"] = "On"
        client.scan["Size X"] = 8
        client.scan["Size Y"] = 8
        client["Autosave Movie"] = "On"
        client["Autosave Movie File Format"] = file_format
        client["Autosave Directory"] = temp_dir
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(.1)
        movie = glob.glob(temp_dir + "/*movie."+file_format.lower())[0]
        s = hs.load(movie, lazy=True)
        if file_format == "MRC":
            assert s.data.shape == (64, 1024, 1024)
        else:
            assert s.data.shape == (1024, 1024, 8,8)
