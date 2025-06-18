import logging
from tifffile import TiffFile
import numpy as np

log = logging.getLogger("DECameraClientLib")


def image_adjust_gain(info_file):
    """A short utility function to read the gain file from the metadata and then perform the necessary
    adjustments to the gain image, (i.e. flipping and binning) to return the gain image in a reduced form.

    Parameters
    ----------
    info_file : str
        The path to the metadata file containing information about the gain file and how the image should be adjusted.

    Returns
    -------
    gain : np.ndarray
        The adjusted gain image as a numpy array.
    """
    original_metadata = {}
    with open(info_file) as metadata:
        for line in metadata.readlines():
            try:
                key, value = line.split("=")
                key = key.strip()
                value = value.strip()
                original_metadata[key] = value
            except ValueError:
                _logger.warning(
                    f"Could not parse line: {line} in metadata file {info_file} "
                    f"Each line should be in the form 'key = value'."
                )
    if original_metadata["Image Processing - Mode"] == "Integrating":
        gain_file = original_metadata[
            "Reference - Integrating Gain"
        ]  # you might have to double check this for Apollo
    else:
        gain_file = original_metadata["Reference - Counting Gain"]
    if "Valid" in gain_file:
        gain_file = gain_file[7:-1]
    elif "Applied" in gain_file:
        gain_file = gain_file[9:-1]
    else:
        raise ValueError("Gain file isn't valid")

    # Load the gain file...
    tiff = TiffFile(gain_file)
    gain = tiff.series[0].asarray()
    if original_metadata["Image Processing - Flip Horizontally"] == "On":
        gain = np.flip(gain, axis=1)
    if original_metadata["Image Processing - Flip Vertically"] == "On":
        gain = np.flip(gain, axis=0)
    if original_metadata["Crop Offset Y"] != "0":
        crop_offset_y = int(original_metadata["Crop Offset Y"])
        gain = gain[crop_offset_y:, :]
    if original_metadata["Crop Offset X"] != "0":
        crop_offset_x = int(original_metadata["Crop Offset X"])
        gain = gain[:, crop_offset_x:]
    shape = gain.shape
    if original_metadata["Binning X"] != "1":
        binx = int(original_metadata["Binning X"])
        gain = gain.reshape(shape[0], shape[1] // binx, binx).mean(axis=2)
    if original_metadata["Binning Y"] != "1":
        biny = int(original_metadata["Binning Y"])
        gain = gain.reshape(shape[0] // biny, biny, shape[1]).mean(axis=1)
    return gain
