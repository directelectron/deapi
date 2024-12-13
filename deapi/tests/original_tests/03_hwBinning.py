import unittest
import sys
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
    propertyName.PROP_FRAME_COUNT: deClient.GetProperty(propertyName.PROP_FRAME_COUNT),
    propertyName.PROP_BINNING_X: deClient.GetProperty(propertyName.PROP_BINNING_X),
    propertyName.PROP_BINNING_Y: deClient.GetProperty(propertyName.PROP_BINNING_Y),
    propertyName.PROP_HARDWARE_BINNING_X: deClient.GetProperty(
        propertyName.PROP_HARDWARE_BINNING_X
    ),
    propertyName.PROP_HARDWARE_BINNING_Y: deClient.GetProperty(
        propertyName.PROP_HARDWARE_BINNING_Y
    ),
}

swBinning = 1
frameCount = 1

deClient.SetProperty(propertyName.PROP_FRAME_COUNT, frameCount)
deClient.SetProperty(propertyName.PROP_BINNING_X, swBinning)
deClient.SetProperty(propertyName.PROP_BINNING_Y, swBinning)


def setProperties(hwSizeX, hwSizeY, binning):
    deClient.SetHWROI(0, 0, hwSizeX, hwSizeY)
    deClient.SetProperty(propertyName.PROP_HARDWARE_BINNING_X, binning)
    deClient.SetProperty(propertyName.PROP_HARDWARE_BINNING_Y, binning)


# Function to be tested
def ImageSize(hwSizeX, hwSizeY, binning):
    setProperties(hwSizeX, hwSizeY, binning)
    imageSizeX = deClient.GetProperty(propertyName.PROP_IMAGE_SIZE_X_PIXELS)
    imageSizeY = deClient.GetProperty(propertyName.PROP_IMAGE_SIZE_Y_PIXELS)
    return func.compare2Value(
        (hwSizeX / binning, hwSizeY / binning), (imageSizeX, imageSizeY), "Image Size: "
    )


def HWFrameSize(hwSizeX, hwSizeY, binning):
    setProperties(hwSizeX, hwSizeY, binning)
    hwFrameSizeX = deClient.GetProperty(propertyName.PROP_HARDWARE_FRAME_SIZE_X)
    hwFrameSizeY = deClient.GetProperty(propertyName.PROP_HARDWARE_FRAME_SIZE_Y)
    return func.compare2Value(
        (hwSizeX / binning, hwSizeY / binning),
        (hwFrameSizeX, hwFrameSizeY),
        "Frame Size: ",
    )


def Shape(hwSizeX, hwSizeY, binning):
    setProperties(hwSizeX, hwSizeY, binning)
    deClient.StartAcquisition()

    hardwareROISizeX = deClient.GetProperty(propertyName.PROP_HARDWARE_ROI_SIZE_X)
    hardwareROISizeY = deClient.GetProperty(propertyName.PROP_HARDWARE_ROI_SIZE_Y)

    image = deClient.GetResult(DEAPI.FrameType.SUMTOTAL, DEAPI.PixelFormat.UINT16)[0]
    return func.compare2Value(
        image.shape,
        (hardwareROISizeX / binning, hardwareROISizeY / binning),
        "Image Shape: ",
    )


# Unit test
class TestHwBinning(unittest.TestCase):

    def testImageSizeWhenBin1(self):
        self.assertTrue(ImageSize(1024, 1024, 1))

    def testImageSizeWhenBin2(self):
        self.assertTrue(ImageSize(1024, 1024, 2))

    def testImageSizeWhenBin3(self):
        self.assertTrue(ImageSize(512, 512, 2))

    def testHwFrameSizeWhenbin1(self):
        self.assertTrue(HWFrameSize(1024, 1024, 1))

    def testHwFrameSizeWhenbin2(self):
        self.assertTrue(HWFrameSize(1024, 1024, 2))

    def testHwFrameSizeWhenbin3(self):
        self.assertTrue(HWFrameSize(512, 512, 2))

    def testShape(self):
        self.assertTrue(Shape(1024, 1024, 2))


if __name__ == "__main__":
    scriptName = os.path.basename(__file__)
    func.writeLogFile(TestHwBinning, scriptName)

    # Reset stdout to the console
    sys.stdout = sys.__stdout__

    # Always ensure that the properties are reset
    for key, value in defaultProperties.items():
        deClient.SetProperty(key, value)
    deClient.Disconnect()
    print("Disconnected from the camera and properties reset.")
