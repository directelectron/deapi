"""
Testing the writing speed for different file types.  This is a good metric for
how fast the file saving is.

This test is run on the server because it requires the server to save the file.
"""

import time
import pytest
import json


class Test4DSaving:
    @pytest.mark.skip(reason="This test is slow and only for testing speed of saving")
    def test_saving(self, client):
        sizes = [128, 256, 512, 1024]
        times = {
            "MRC": {s: [] for s in sizes},
            "DE5": {s: [] for s in sizes},
            "HSPY": {s: [] for s in sizes},
        }
        for size in sizes:
            for i in range(3):
                for file_format in ["MRC", "DE5", "HSPY"]:
                    times[file_format][size].append(
                        self.save(client, size, file_format)
                    )

        version = client["Server Software Version"]
        fname = version + "_saving_speed.json"
        with open(fname, "w") as outfile:
            json.dump(times, outfile)

    def save(self, client, size=64, file_format="MRC"):
        client["Frames Per Second"] = 100
        client["Scan - Enable"] = "On"
        client.scan["Size X"] = 64
        client.scan["Size Y"] = 64
        client["Grabbing - Target Buffer Size (MB)"] = (
            32  # 32 MB buffer (This might change things
        )
        client["Hardware ROI Offset X"] = (client["Sensor Size X (pixels)"] - size) // 2
        client["Hardware ROI Offset Y"] = (client["Sensor Size X (pixels)"] - size) // 2
        client["Hardware ROI Size X"] = size
        client["Hardware ROI Size Y"] = size

        client["Autosave Movie"] = "On"
        client["Autosave Movie File Format"] = file_format
        client["Autosave Directory"] = "D:\Temp"
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(0.1)
        print(client["Speed - Frame Write Time (us)"])
        return client["Speed - Frame Write Time (us)"]


class TestCompressionSpeed:

    @pytest.mark.engineering
    @pytest.mark.server
    @pytest.mark.skip(reason="Not implemented yet")
    def test_compression_speeds(self, client):
        methods = ["lz4"]  # zstd throws an error???
        levels = [5, 7, 9]

        compression_times = {
            "lz4": {l: [] for l in levels},
        }
        for method in methods:
            for level in levels:
                client["Compression - Mode"] = method
                client["Compression - Level"] = level
                client["Compression - Threads"] = 8  # Max is half the number of cores
                client["Grabbing - Target Buffer Size (MB)"] = 32
                assert client["Compression - Mode"] == method
                assert client["Compression - Level"] == level
                client["Frames Per Second"] = 300
                client["Scan - Enable"] = "On"
                client.scan["Size X"] = 64
                client.scan["Size Y"] = 64
                client["Autosave Movie"] = "On"
                client["Autosave 4D File Format"] = "H5EBSD"
                client["Autosave Directory"] = "D:\Temp"
                client.start_acquisition(1)
                while client.acquiring:
                    time.sleep(0.1)
                time.sleep(2)
                processing_log = (
                    client["Autosave Movie Frames File Path"].split("0_movie")[0]
                    + "processing.log"
                )
                with open(processing_log, "r") as f:
                    lines = f.readlines()
                summary_index = 0
                for i, l in enumerate(lines):
                    if "Summary" in l:
                        summary_index = i

                summary_dict = {}
                for l in lines[summary_index + 2 :]:
                    try:
                        key, values = l.split("=")
                        key = key.strip()
                        summary_dict[key] = values.strip()
                    except ValueError:
                        pass
                print(
                    f"{method}-{level}: {summary_dict['Compression Speed(per core)']}"
                )
                compression_times[method][level] = summary_dict[
                    "Compression Speed(per core)"
                ].split(" ")[0]
        print(compression_times)
        version = client["Server Software Version"]
        fname = version + "_compression_speed.json"
        with open(fname, "w") as outfile:
            json.dump(compression_times, outfile)


class TestCompressionSlow:

    @pytest.mark.engineering
    @pytest.mark.server
    @pytest.mark.skip(reason="Not implemented yet")
    def test_compression_speeds(self, client):
        method = "zlib"
        level = 4

        client["Compression - Mode"] = method
        client["Compression - Level"] = level
        client["Compression - Threads"] = 8  # Max is half the number of cores
        client["Grabbing - Target Buffer Size (MB)"] = 32
        assert client["Compression - Mode"] == method
        assert client["Compression - Level"] == level
        client["Frames Per Second"] = 300
        client["Scan - Enable"] = "On"
        client.scan["Size X"] = 64
        client.scan["Size Y"] = 64
        client["Autosave Movie"] = "On"
        client["Autosave 4D File Format"] = "H5EBSD"
        client["Autosave Directory"] = "D:\Temp"
        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(0.1)

        time.sleep(2)
        processing_log = (
            client["Autosave Movie Frames File Path"].split("0_movie")[0]
            + "processing.log"
        )
        with open(processing_log, "r") as f:
            lines = f.readlines()
        summary_index = 0
        for i, l in enumerate(lines):
            if "Summary" in l:
                summary_index = i

        summary_dict = {}
        for l in lines[summary_index + 2 :]:
            try:
                key, values = l.split("=")
                key = key.strip()
                summary_dict[key] = values.strip()
            except ValueError:
                pass
        print(summary_dict["Compression Speed(per core)"])
