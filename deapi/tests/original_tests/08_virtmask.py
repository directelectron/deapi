import sys
import numpy
import unittest
from PIL import Image
import os

import deapi as DEAPI
from deapi.tests.original_tests import func, propertyName

# Connect to the server
deClient = DEAPI.Client()
deClient.Connect()
cameras = deClient.ListCameras()
camera = cameras[0]
deClient.SetCurrentCamera(camera)
serverVersion = deClient.GetProperty(propertyName.PROP_SERVER_SOFTWARE_VERSION)
cameraName = deClient.GetProperty(propertyName.PROP_CAMERA_NAME)
print(f"Camera Name: {cameraName}, Server Software Version is: {serverVersion}")

# Store default properties in a dictionary
defaultProperties = {
    propertyName.PROP_AUTOSAVE_MOVIE: deClient.GetProperty(
        propertyName.PROP_AUTOSAVE_MOVIE
    ),
    propertyName.PROP_SCAN_ENABLE: deClient.GetProperty(propertyName.PROP_SCAN_ENABLE),
    propertyName.PROP_EXPOSURE_MODE: deClient.GetProperty(
        propertyName.PROP_EXPOSURE_MODE
    ),
}

deClient.SetProperty(propertyName.PROP_AUTOSAVE_MOVIE, "Save")
deClient.SetProperty(propertyName.PROP_EXPOSURE_MODE, "Normal")
deClient.SetProperty(propertyName.PROP_SCAN_ENABLE, "On")


# virtmask size
virtMaskHeight = 1024
virtMaskWidth = 1024


def testFirst200Pixels(Image, maskID):
    # Set initial ROI size
    deClient.SetHWROI(0, 0, 1024, 1024)

    # Create virtual mask and set the first 200 pixel values to 2
    mask = numpy.zeros((virtMaskHeight, virtMaskWidth), dtype=numpy.uint8)
    mask[:200, :] = 2

    virPropertyName = f"Scan - Virtual Detector {maskID} Shape"
    deClient.SetProperty(virPropertyName, "Arbitrary")

    if not deClient.SetVirtualMask(maskID, virtMaskHeight, virtMaskWidth, mask):
        return False

    # Define attributes and frame type
    attributes = DEAPI.Attributes()
    frameType = getattr(DEAPI.FrameType, f"VIRTUAL_MASK{maskID}")

    # Generate and check the first image
    Image, _, _, _ = deClient.GetResult(frameType, DEAPI.PixelFormat.AUTO, attributes)

    # Flatten the image to a 1D array for easy checking
    flattenedImage = Image.flatten()

    if not numpy.all(flattenedImage[:204800] == 2) or not numpy.all(
        flattenedImage[204800:] == 0
    ):
        return False
    # return func.compare2Value()
    # Update ROI size
    deClient.SetHWROI(0, 0, 512, 512)

    # Generate and check the second image
    Image, _, _, _ = deClient.GetResult(frameType, DEAPI.PixelFormat.AUTO, attributes)

    # Flatten the image to a 1D array for easy checking
    flattenedImage = Image.flatten()

    if not numpy.all(flattenedImage[:51200] == 2) or not numpy.all(
        flattenedImage[51200:] == 0
    ):
        return False

    return True


# Unit test
class testVirtmask(unittest.TestCase):
    # Set pixels: 2
    def testVirtMask1(self):
        self.assertTrue(testFirst200Pixels(Image, 1))

    def testVirtMask2(self):
        self.assertTrue(testFirst200Pixels(Image, 2))

    def testVirtMask3(self):
        self.assertTrue(testFirst200Pixels(Image, 3))

    def testVirtMask4(self):
        self.assertTrue(testFirst200Pixels(Image, 4))


if __name__ == "__main__":
    scriptName = os.path.basename(__file__)
    func.writeLogFile(testVirtmask, scriptName)

    # Reset stdout to the console
    sys.stdout = sys.__stdout__

    # Always ensure that the properties are reset
    for key, value in defaultProperties.items():
        deClient.SetProperty(key, value)
    deClient.Disconnect()
    print("Disconnected from the camera and properties reset.")
