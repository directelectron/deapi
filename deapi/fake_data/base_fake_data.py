import numpy as np
from skimage.transform import resize


class FlatFakeData:

    def __init__(self, fake_data):
        self.fake_data = fake_data

    def __getitem__(self, item):
        labels = self.fake_data.navigator.flat[item].astype(int)
        dp = self.fake_data.signal[labels]
        return dp


class BaseFakeData:
    """
    The idea of this class is to provide a base class for fake data generation.

    Other classes will inherit from this class and then implement, or override certain methods.
    """

    def __init__(self, navigator=None, signal=None, server=None):
        """
        Data is generated from a given navigator and signal arrays. The navigator array should
        be a ND array of labels with the maximum value (M) equal to the length of the number of
        signals.

        The signal array should be Mx2D arrays of data corresponding to the Signal at each navigator.

        Virtual Images are then created by only calculating the virtual image from each of the M signals
        and then substituting the result into the navigator array!
        """
        self.navigator = np.array(navigator).astype(int)
        self._signal = np.array(signal)
        self.server = server
        self.flat = FlatFakeData(self)

    @property
    def signal(self):
        """
        Slice the signal array given the parameters from the server if initialized.
        """
        s = self._signal
        if self.server is None:
            return s
        else:
            hw_roi = s[
                :,
                int(self.server["Hardware ROI Offset X"]) : int(
                    self.server["Hardware ROI Offset X"]
                )
                + int(self.server["Hardware ROI Size X"]),
                int(self.server["Hardware ROI Offset Y"]) : int(
                    self.server["Hardware ROI Offset Y"]
                )
                + int(self.server["Hardware ROI Size Y"]),
            ]
            shape = (
                4,
                int(self.server["Hardware Binning X"]),
                hw_roi.shape[1] // int(self.server["Hardware Binning X"]),
                int(self.server["Hardware Binning Y"]),
                hw_roi.shape[2] // int(self.server["Hardware Binning Y"]),
            )
            binned_roi = hw_roi.reshape(shape).sum(axis=(1, 3))

            # handling both is a bit tricky
            """
            sw_roi = binned_roi[self.server['Crop Offset X']:self.server['Crop Size X']+self.server['Crop Offset X'],
                                self.server['Crop Offset Y']:self.server['Crop Size Y']+self.server['Crop Offset Y']]
            sw_binned_roi = sw_roi.reshape(self.server["Binning X"],
                                             sw_roi.shape[0] // self.server["Binning X"],
                                             self.server["Binning Y"],
                                             sw_roi.shape[1]//self.server["Binning Y"]).sum(axis=(0,2))
            """
            return binned_roi

    def __getitem__(self, item):
        """
        Get the signal at the given item in the navigator array.
        """
        labels = self.navigator[item].astype(int)
        dp = self.signal[labels]

        return dp

    def get_virtual_image(self, virtual_mask, method="Sum"):
        """
        Get the virtual image at the given item in the navigator array.
        """
        if virtual_mask.shape != self.signal.shape[1:]:
            virtual_mask = resize(
                virtual_mask,
                (self.signal.shape[1], self.signal.shape[2]),
                preserve_range=True,
            ).astype(np.int8)

        positive = virtual_mask == 2
        negative = virtual_mask == 0
        s = self.signal

        if method == "Sum":
            values = np.sum(s * positive[np.newaxis], axis=(1, 2))
        elif method == "Difference":
            values = np.sum(s * positive[np.newaxis], axis=(1, 2)) - np.sum(
                s * negative[np.newaxis], axis=(1, 2)
            )
        else:
            raise ValueError(
                f"Method {method} not recognized. Please use 'sum' or 'difference'"
            )
        return values[self.navigator]
