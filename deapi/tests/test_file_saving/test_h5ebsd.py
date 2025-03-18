"""

This module tests file saving for h5EBSD files


This should be run before any release to make sure that the file loaders downstream
work.
"""

import os
import time

import blosc2
import numpy as np
import pytest
import hyperspy.api as hs
import glob
import h5py



class TestSavingHyperSpy:
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

    @pytest.mark.server
    def test_initialize(self, client):
        client["Frames Per Second"] = 100
        client["Scan - Enable"] = "On"
        client.scan["Size X"] = 8
        client.scan["Size Y"] = 8
        client["Autosave Movie"] = "On"
        client["Autosave 4D File Format"] = "H5EBSD"
        print(client.get_property_spec("Autosave 4D File Format"))
        assert client["Autosave 4D File Format"] == "H5EBSD"

    @pytest.mark.server
    def test_save_hspy_4DSTEM(self, client):
        if not os.path.exists("D:\Temp"):
            os.mkdir("D:\Temp")
        if not os.path.exists("D:\Temp\HSPY"):
            os.mkdir("D:\Temp\HSPY")
        temp_dir = "D:\Temp\HSPY"
        client["Frames Per Second"] = 100
        client["Scan - Enable"] = "On"
        client.scan["Size X"] = 8
        client.scan["Size Y"] = 8
        client["Autosave Movie"] = "On"
        client["Autosave 4D File Format"] = "HSPY"
        client["Autosave Directory"] = temp_dir
        client
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(0.1)
        time.sleep(2)
        assert os.path.exists(client["Autosave Movie Frames File Path"])
        print(client["Autosave Movie Frames File Path"])
        h5py.File(client["Autosave Movie Frames File Path"], "r")

    @pytest.mark.parametrize("compression", ["blosclz", "lz4", "zstd", "zlib"])
    @pytest.mark.server
    @pytest.mark.engineering
    def test_set_compression(self, client, compression):
        client["Compression - Mode"] = compression
        assert client["Compression - Mode"] == compression.lower()
        if not os.path.exists("D:\Temp"):
            os.mkdir("D:\Temp")
        if not os.path.exists("D:\Temp\H5EBSD"):
            os.mkdir("D:\Temp\H5EBSD")
        temp_dir = "D:\Temp\H5EBSD"
        client["Frames Per Second"] = 100
        client["Scan - Enable"] = "On"
        client.scan["Size X"] = 8
        client.scan["Size Y"] = 8

        client[""] = 8
        client.scan["Size Y"] = 8
        client["Autosave Movie"] = "On"
        client["Grabbing - Target Buffer Size (MB)"] = 16
        client["Autosave 4D File Format"] = "H5EBSD"
        client["Autosave Directory"] = temp_dir
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(0.1)
        time.sleep(2)
        assert os.path.exists(client["Autosave Movie Frames File Path"])
        s = client["Autosave Movie Frames File Path"]
        f2 = h5py.File(s, "r")
        dset = f2["Scan 1/EBSD/Data/patterns"]
        d = dset[:]
        assert d.shape == (64, 1024, 1024)



    @pytest.mark.parametrize("buffer", [8,16])
    @pytest.mark.server
    def test_save_EBSD(self, client, buffer):
        if not os.path.exists("D:\Temp"):
            os.mkdir("D:\Temp")
        if not os.path.exists("D:\Temp\H5EBSD"):
            os.mkdir("D:\Temp\H5EBSD")
        temp_dir = "D:\Temp\H5EBSD"
        client["Frames Per Second"] = 200
        client["Scan - Enable"] = "On"
        client.scan["Size X"] = 8
        client.scan["Size Y"] = 8
        client["Autosave Movie"] = "On"
        client["Grabbing - Target Buffer Size (MB)"] = buffer
        client["Autosave 4D File Format"] = "H5EBSD"
        client["Autosave Directory"] = temp_dir
        client["Hardware ROI Offset X"] = 512-128
        client["Hardware ROI Offset Y"] = 512-128
        client["Hardware Binning X"] = 2
        client["Hardware Binning Y"] = 2
        client["Hardware ROI Size X"] = 256
        client["Hardware ROI Size Y"] = 256
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(0.1)
        time.sleep(2)
        assert os.path.exists(client["Autosave Movie Frames File Path"])

        print(client["Autosave Movie Frames File Path"])
        f = h5py.File(client["Autosave Movie Frames File Path"], "r+")
        dset = f["Pattern Data"]["Patterns"]
        d = dset[:]
        assert d.shape == (64, 128, 128)
        time.sleep(4)

    @pytest.mark.server
    def test_save_EBSD_large(self, client):
        if not os.path.exists("D:\Temp"):
            os.mkdir("D:\Temp")
        if not os.path.exists("D:\Temp\H5EBSD"):
            os.mkdir("D:\Temp\H5EBSD")
        temp_dir = "D:\Temp\H5EBSD"
        client.set_engineering_mode(enable=True, password="woohoo!")
        client["Frames Per Second"] = 400
        client["Scan - Enable"] = "On"
        client.scan["Size X"] = 64
        client.scan["Size Y"] = 64
        client["Autosave Movie"] = "On"
        client["Grabbing - Target Buffer Size (MB)"] = 32
        client["Autosave 4D File Format"] = "H5EBSD"
        client["Autosave Directory"] = temp_dir
        client["Compression - Mode"] = "BLOSCLZ"

        client.start_acquisition(1)
        tic = time.time()
        while client.acquiring:
            time.sleep(0.1)
        toc = time.time()

        print(f"Time to acquire: {toc-tic}")
        total_frames =  client.scan["Size X"]*client.scan["Size Y"]
        estimated_time  = total_frames/client["Frames Per Second"]
        print(f"Estimated time to acquire: {estimated_time}")
        time.sleep(2)
        assert os.path.exists(client["Autosave Movie Frames File Path"])
        print(client["Autosave Movie Frames File Path"])
        f2 = h5py.File(client["Autosave Movie Frames File Path"], "r")


    @pytest.mark.server
    def test_save_EBSD_stop(self, client):
        if not os.path.exists("D:\Temp"):
            os.mkdir("D:\Temp")
        if not os.path.exists("D:\Temp\H5EBSD"):
            os.mkdir("D:\Temp\H5EBSD")
        temp_dir = "D:\Temp\H5EBSD"
        client["Frames Per Second"] = 200
        client["Scan - Enable"] = "On"
        client.scan["Size X"] = 128
        client.scan["Size Y"] = 128
        client["Autosave Movie"] = "On"
        client["Grabbing - Target Buffer Size (MB)"] = 16
        client["Autosave 4D File Format"] = "H5EBSD"
        client["Autosave Directory"] = temp_dir
        client["Compression - Mode"] = "BLOSCLZ"

        client.start_acquisition(1)
        assert client.acquiring
        time.sleep(15)
        client.stop_acquisition()
        assert os.path.exists(client["Autosave Movie Frames File Path"])
        print(client["Autosave Movie Frames File Path"])
        f2 = h5py.File(client["Autosave Movie Frames File Path"], "r")

        assert f2["Scan 1/EBSD/Data/patterns"].chunks == (8, 1024, 1024)
        assert f2["Scan 1/EBSD/Data/patterns"].shape[0] < 128*128
