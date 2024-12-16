"""
Testing the transfer speed of the movie buffer.  This is a good metric for
understanding how fast the server can transfer data to the client.

This test is run on the server because it requires the server to save the file.
"""

import time
import pytest
import json
from deapi.data_types import MovieBufferStatus
import numpy as np
import matplotlib.pyplot as plt


class TestBufferTransfer:
    @pytest.mark.skip(reason="This test is slow and only for testing speed of saving")
    def test_transfer(self, client):
        client["Frames Per Second"] = 60  # ~1 GB/s
        targets = [2, 4, 8, 16, 32, 64]
        speed = []
        for target in targets:
            client["Grabbing - Target Buffer Size (MB)"] = target
            client.scan(size_x=5, size_y=5, enable="On")
            client.start_acquisition(1, requestMovieBuffer=True)
            numberFrames = 0
            index = 0
            status = MovieBufferStatus.OK
            success = True
            info, buffer, total_bytes, numpy_dtype = client.current_movie_buffer()
            number_frames = 0
            times = []
            while status == MovieBufferStatus.OK and success:
                tic = time.time()
                status, total_bytes, number_frames, buffer = client.GetMovieBuffer(
                    buffer, total_bytes, number_frames
                )

                ## CovertToImage(movieBuffer, headerBytes, dataType, imageW, imageH, numberFrames);
                frameIndexArray = np.frombuffer(
                    buffer, np.longlong, offset=0, count=numberFrames
                )
                movieBuffer = np.frombuffer(
                    buffer,
                    dtype=numpy_dtype,
                    offset=info.headerBytes,
                    count=info.imageH * info.imageW * numberFrames,
                )
                toc = time.time()
                times.append(total_bytes / (toc - tic))

            speed.append(np.mean(times))
        all_speeds = np.vstack((targets, speed))
        np.save("buffer_speeds.npy", all_speeds)
