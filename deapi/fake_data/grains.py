from skimage.segmentation import expand_labels
import numpy as np
from skimage.draw import disk

from deapi.fake_data.base_fake_data import BaseFakeData


class TiltGrains(BaseFakeData):

    def __init__(
        self,
        seed=0,
        x_pixels=512,
        y_pixels=512,
        kx_pixels=512,
        ky_pixels=512,
        num_grains=4,
        server=None,
    ):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.x_pixels = x_pixels
        self.y_pixels = y_pixels
        self.kx_pixels = kx_pixels
        self.ky_pixels = ky_pixels
        self.num_grains = num_grains
        grains = self.create_grains(x_pixels, y_pixels, num_grains, seed)
        self.rotations = self.rng.uniform(0, 2 * np.pi, num_grains)
        dps = [
            self.create_fake_diffraction_data(
                kx_pixels,
                ky_pixels,
                rotation=r,
                intensity=i * 10,
            )
            for r, i in enumerate(self.rotations)
        ]
        super().__init__(grains, dps, server=server)

    def create_fake_diffraction_data(
        self,
        kx_pixels=512,
        ky_pixels=512,
        rotation=0,
        radius=None,
        intensity=10,
        dtype=np.int16,
    ):
        """
        Fake data is created from 4 diffraction patterns which are seperated into Grains.
        This means that we only have to calculate the virtual image from each of the 4 diffraction
        patterns and then we can "Create" any of the virtual images that we want!
        """
        dp = np.ones((kx_pixels, ky_pixels), dtype=dtype)
        if radius is None:
            radius = kx_pixels / 20
        center = (kx_pixels // 2, ky_pixels // 2)
        distance = kx_pixels * 0.3
        rr, cc = disk(center, radius=radius)
        dp[rr, cc] = intensity * 10

        for theta in np.linspace(0, np.pi * 2, 7):
            delta = (
                np.array((np.cos(theta + rotation), np.sin(theta + rotation)))
                * distance
            )
            rr, cc = disk(np.add(center, delta), radius=radius)
            dp[rr, cc] = intensity * 7
        return dp

    def create_grains(
        self,
        x_pixels=512,
        y_pixels=512,
        num_grains=4,
        seed=0,
        size=40,
    ):
        rng = np.random.default_rng(seed)
        x = rng.integers(0, x_pixels, size=num_grains)
        y = rng.integers(0, y_pixels, size=num_grains)

        navigator = np.zeros((x_pixels, y_pixels))
        for i in range(num_grains):
            navigator[x[i], y[i]] = i
        navigator = expand_labels(navigator, distance=x_pixels * 2)
        return navigator
