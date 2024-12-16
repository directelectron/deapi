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
