"""
Tests for virtual image buffer acquisition.

Verifies that, while an acquisition is running with ``queue_virtual_buffers=True``
and ``Scan - Repeats = 5``, all 5 virtual detector buffers (ids 0–4) can be
streamed and contain valid image data.
"""

import numpy as np
import pytest

from deapi.data_types import MovieBufferStatus, VirtualImageInfo, DataType

NUM_VIRTUAL_BUFFERS = 5


class TestVirtualImageBuffers:

    @pytest.fixture(autouse=True)
    def clean_state(self, client):
        """Reset relevant properties to a known state before each test."""
        client.stop_acquisition()
        client["Hardware Binning X"] = 1
        client["Hardware Binning Y"] = 1
        client["Hardware ROI Offset X"] = 0
        client["Hardware ROI Offset Y"] = 0
        client["Hardware ROI Size X"] = 1024
        client["Hardware ROI Size Y"] = 1024
        client["Binning X"] = 1
        client["Binning Y"] = 1
        client["Frames Per Second"] = 1000
        client["Scan - Type"] = "Raster"
        client["Scan - Size X"] = 4
        client["Scan - Size Y"] = 4
        client["Scan - Enable"] = "On"
        client["Scan - Repeats"] = 1
        client["Scan - Repeat Delay (seconds)"] = 0

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    @pytest.mark.server
    def test_virtual_image_info_has_valid_dimensions(self, client):
        """get_virtual_image_buffer_info() returns valid dimensions once acquisition starts."""
        info = client.get_virtual_image_buffer_info()

        client.start_acquisition(
            number_of_acquisitions=1,
            queue_virtual_buffers=True,
        )

        assert isinstance(info, VirtualImageInfo)
        assert info.width > 0, "Virtual image width must be > 0"
        assert info.height > 0, "Virtual image height must be > 0"
        assert info.buffer_size > 0, "Virtual image buffer_size must be > 0"
        byte_num = 4 if info.data_type == DataType.DE32f else 2
        assert info.buffer_size == info.width * info.height * byte_num

    @pytest.mark.server
    def test_streaming_all_virtual_buffers(self, client):
        """Stream virtual image buffers for all detector channels while acquiring.

        With ``Scan - Repeats = 5`` and 5 virtual detector channels (ids 0–4),
        we expect exactly 5 frames × 5 channels = 25 valid images before the
        server signals ``FINISHED``.
        """
        num_repeats = 5
        client["Scan - Repeats"] = num_repeats
        assert client["Scan - Repeats"] == num_repeats
        # Fetch metadata immediately after starting — the server knows image
        # dimensions before frames arrive.

        info = client.get_virtual_image_buffer_info()
        assert info.width > 0 and info.height > 0, "Invalid virtual image dimensions"

        client["Scan - Virtual Detector 1 Shape"] = "Ellipse"
        client["Scan - Virtual Detector 2 Shape"] = "Ellipse"
        client["Scan - Virtual Detector 3 Shape"] = "Ellipse"
        client["Scan - Virtual Detector 4 Shape"] = "Ellipse"
        client.start_acquisition(
            number_of_acquisitions=1,
            queue_virtual_buffers=True,
        )

        received_frames: list[tuple[int, int, int, np.ndarray]] = []
        # UNKNOWN = 0, FAILED = 1, TIMEOUT = 3, FINISHED = 4, OK = 5
        # OK --> Still more frames to access

        finished = False

        while not finished:
            for buf_id in range(NUM_VIRTUAL_BUFFERS):
                status, frame_index, pattern_index, image = (
                    client.get_virtual_image_buffer(buf_id, virtual_image_info=info)
                )
                print(
                    f"buf_id={buf_id} frame={frame_index} pattern={pattern_index} status={status} image shape: {image.shape if image is not None else None}"
                )

                if status == MovieBufferStatus.OK:
                    assert (
                        image is not None
                    ), f"buf_id={buf_id} frame={frame_index} pattern={pattern_index}: status OK but image is None"
                    assert image.shape == (
                        info.height,
                        info.width,
                    ), f"buf_id={buf_id} frame={frame_index} pattern={pattern_index}: unexpected shape {image.shape}"
                    received_frames.append((buf_id, frame_index, pattern_index, image))

                elif status == MovieBufferStatus.FINISHED:
                    finished = True
                    # This channel is done — mark finished.

                elif status == MovieBufferStatus.TIMEOUT:
                    print(
                        f"buf_id={buf_id} frame={frame_index} pattern={pattern_index}: timeout waiting for frame"
                    )
                    # This can happen if we check a channel before its first frame is ready.
                    # Just ignore and check again in the next loop iteration.

                elif status == MovieBufferStatus.FAILED:
                    print(
                        f"buf_id={buf_id} frame={frame_index} pattern={pattern_index}: failed to retrieve frame-- Likely this"
                        f"virtual image is not initialized."
                    )

        expected_total = num_repeats * NUM_VIRTUAL_BUFFERS
        assert (
            len(received_frames) == expected_total
        ), f"Expected {expected_total} frames, got {len(received_frames)}"

    @pytest.mark.server
    def test_streaming_all_virtual_buffers_one_off(self, client):
        """Stream virtual image buffers for all detector channels while acquiring.

        With ``Scan - Repeats = 5`` and 5 virtual detector channels (ids 0–4),
        we expect exactly 5 frames × 5 channels = 25 valid images before the
        server signals ``FINISHED``.
        """
        num_repeats = 5
        client["Scan - Repeats"] = num_repeats
        assert client["Scan - Repeats"] == num_repeats
        # Fetch metadata immediately after starting — the server knows image
        # dimensions before frames arrive.

        info = client.get_virtual_image_buffer_info()
        assert info.width > 0 and info.height > 0, "Invalid virtual image dimensions"

        client["Scan - Virtual Detector 1 Shape"] = "Ellipse"
        client["Scan - Virtual Detector 2 Shape"] = "Ellipse"
        client["Scan - Virtual Detector 3 Shape"] = "Ellipse"
        client["Scan - Virtual Detector 4 Shape"] = "Off"
        client.start_acquisition(
            number_of_acquisitions=1,
            queue_virtual_buffers=True,
        )

        received_frames: list[tuple[int, int, int, np.ndarray]] = []
        # UNKNOWN = 0, FAILED = 1, TIMEOUT = 3, FINISHED = 4, OK = 5
        # OK --> Still more frames to access

        finished = False

        while not finished:
            for buf_id in range(NUM_VIRTUAL_BUFFERS):
                status, frame_index, pattern_index, image = (
                    client.get_virtual_image_buffer(buf_id, virtual_image_info=info)
                )
                print(
                    f"buf_id={buf_id} frame={frame_index} pattern={pattern_index} status={status} image shape: {image.shape if image is not None else None}"
                )

                if buf_id == 4:
                    assert status == MovieBufferStatus.FAILED
                if status == MovieBufferStatus.OK:
                    assert (
                        image is not None
                    ), f"buf_id={buf_id} frame={frame_index} pattern={pattern_index}: status OK but image is None"
                    assert image.shape == (
                        info.height,
                        info.width,
                    ), f"buf_id={buf_id} frame={frame_index} pattern={pattern_index}: unexpected shape {image.shape}"
                    received_frames.append((buf_id, frame_index, pattern_index, image))

                elif status == MovieBufferStatus.FINISHED:
                    finished = True
                    # This channel is done — mark finished.

                elif status == MovieBufferStatus.TIMEOUT:
                    print(
                        f"buf_id={buf_id} frame={frame_index} pattern={pattern_index}: timeout waiting for frame"
                    )
                    # This can happen if we check a channel before its first frame is ready.
                    # Just ignore and check again in the next loop iteration.

                elif status == MovieBufferStatus.FAILED:
                    print(
                        f"buf_id={buf_id} frame={frame_index} pattern={pattern_index}: failed to retrieve frame-- Likely this"
                        f"virtual image is not initialized."
                    )

        expected_total = num_repeats * (NUM_VIRTUAL_BUFFERS - 1)
        assert (
            len(received_frames) == expected_total
        ), f"Expected {expected_total} frames, got {len(received_frames)}"

    @pytest.mark.server
    def test_streaming_multiple_xy_arrays(self, client):
        """Stream virtual image buffers from multiple XY arrays"""
        num_repeats = 10

        # create 100 patterns that are 128 x 128 in size with only 10% of the points filled in.
        state = np.random.RandomState(0)
        coords = []

        for i in range(100):
            mask = np.ones((128, 128), dtype=bool)
            # randomly remove 95% of the points
            mask[state.random(mask.shape) < 0.95] = False
            # turn the mask into a list of xy coordinates
            coords.append(np.argwhere(mask).astype(int))

        client.set_xy_array(coords, height=128, width=128)

        client["Scan - Repeats"] = num_repeats
        assert client["Scan - Repeats"] == num_repeats

        info = client.get_virtual_image_buffer_info()
        assert info.width == 128
        assert info.height == 128

        # Set up the virtual images...

        client["Scan - Virtual Detector 1 Shape"] = "Ellipse"
        client["Scan - Virtual Detector 2 Shape"] = "Ellipse"
        client["Scan - Virtual Detector 3 Shape"] = "Ellipse"
        client["Scan - Virtual Detector 4 Shape"] = "Off"

        client.start_acquisition(
            number_of_acquisitions=1,
            queue_virtual_buffers=True,
        )

        received_frames: list[tuple[int, int, int, np.ndarray]] = []
        # UNKNOWN = 0, FAILED = 1, TIMEOUT = 3, FINISHED = 4, OK = 5
        # OK --> Still more frames to access

        finished = False

        while not finished:
            # cycle though and get the virtual images and get the buffer.
            for buf_id in range(NUM_VIRTUAL_BUFFERS):
                got_frame = False
                while not got_frame:
                    status, frame_index, pattern_index, image = (
                        client.get_virtual_image_buffer(
                            buf_id, virtual_image_info=info, timeout_msec=1000  # 1 sec
                        )
                    )
                    if status == MovieBufferStatus.OK:
                        received_frames.append(
                            (buf_id, frame_index, pattern_index, image)
                        )  # Do whatever with the frame.
                        got_frame = True

                    elif status == MovieBufferStatus.FINISHED:
                        finished = True
                        # This channel is done — mark finished.
                        got_frame = True

                    elif status == MovieBufferStatus.TIMEOUT:
                        got_frame = False
                    elif status == MovieBufferStatus.FAILED:
                        print(
                            f"buf_id={buf_id} frame={frame_index} pattern={pattern_index}: failed to retrieve frame-- Likely this"
                            f" virtual image is not initialized."
                        )
                        got_frame = True
