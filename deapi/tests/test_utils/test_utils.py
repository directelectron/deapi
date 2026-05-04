import numpy as np
import pytest
import time
import hyperspy.api as hs

from deapi.utils import image_adjust_gain


@pytest.fixture(scope="session")
def gain_references(client):
    """Take dark and gain references once per session, reused across all parametrized tests."""
    client["Image Processing - Flatfield Correction"] = "Dark and Gain"
    client["Scan - Enable"] = "Off"
    client["Exposure Mode"] = "Normal"
    client["Test Pattern"] = "SW Constant 1"
    client["Frames Per Second"] = 100
    client.take_dark_reference(100)
    client["Image Processing - Apply Gain on Movie"] = "Off"
    client["Test Pattern"] = "SW Four Parts"
    client.take_gain_reference(100, target_electrons_per_pixel=100)


class TestUtils:
    """Test class for utility functions in deapi.utils."""

    @pytest.mark.server
    @pytest.mark.parametrize("binx", [1, 2, 4])
    @pytest.mark.parametrize("offset_y", [0, 4, 16])
    @pytest.mark.parametrize("flip_horizontal", [False, True])
    @pytest.mark.parametrize("flip_vertical", [False, True])
    def test_image_adjust_gain(
        self, client, gain_references, binx, offset_y, flip_horizontal, flip_vertical
    ):
        """Test the image adjustment function."""
        client["Binning Y"] = 1
        client["Binning X"] = binx
        client["Crop Offset Y"] = offset_y
        client["Crop Size Y"] = 1024 - offset_y
        client["Image Processing - Flip Horizontally"] = (
            "On" if flip_horizontal else "Off"
        )
        client["Image Processing - Flip Vertically"] = "On" if flip_vertical else "Off"
        client["Image Processing - Flatfield Correction"] = "Dark and Gain"
        client["Image Processing - Apply Gain on Movie"] = "Off"
        client["Image Processing - Apply Gain on Final"] = "On"
        client["Autosave Final Image"] = "On"
        client["Autosave Movie"] = "On"

        client.start_acquisition(10)
        while client.acquiring:
            time.sleep(0.1)

        final_image_path = client["Autosave Final Image File Path"]
        movie_path = client["Autosave Movie Frames File Path"]

        final_image = hs.load(final_image_path).data
        movie = hs.load(movie_path).data.astype(np.float32)
        np.testing.assert_array_almost_equal(final_image[0, 0], final_image, decimal=1)
        assert np.not_equal(
            final_image, movie
        ).any(), "Movie should not be equal to final image after gain adjustment"
        info_file = final_image_path.replace("final.mrc", "info.txt")
        adjusted_gain = image_adjust_gain(info_file)
        adjusted_movie_final = np.sum(movie, axis=0) * adjusted_gain
        np.testing.assert_array_almost_equal(
            final_image[0, 0], adjusted_movie_final, decimal=-1
        )

    @pytest.mark.server
    def test_get_gain(self, client):
        client["Exposure Mode"] = "Normal"
        client["Test Pattern"] = "SW Constant 1"
        client["Frames Per Second"] = 100
        client.take_dark_reference(100)
        client["Test Pattern"] = "SW Four Parts"
        client["Exposure Mode"] = "Gain"
        client["Exposure Time (seconds)"] = 1
        prev_gain = client["Reference - Integrating Gain"]
        client.start_acquisition(2)
        while client.acquiring:
            time.sleep(0.1)
        # Poll until gain is applied instead of sleeping
        deadline = time.time() + 10
        while client["Reference - Integrating Gain"] == prev_gain and time.time() < deadline:
            time.sleep(0.2)
        assert (
            client["Reference - Integrating Gain"] != prev_gain
        ), "Gain should have been applied"
        client["Exposure Mode"] = "Normal"
        client["Autosave Final Image"] = "On"
        client["Image Processing - Apply Gain on Final"] = "On"

        client.start_acquisition(1)
        while client.acquiring:
            time.sleep(0.1)
        final_image_path = client["Autosave Final Image File Path"]
        f = open(final_image_path, "rb")
        final_img = np.memmap(
            f, offset=1024, dtype=np.float32, mode="r", shape=(1024, 1024)
        )
        np.testing.assert_array_almost_equal(final_img[0, 0], final_img, decimal=1)
