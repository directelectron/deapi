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

frameCount = 1
deClient.SetProperty("Frame Count", frameCount)


def setProperties(hwSizeX, hwSizeY, swBinning, hwBinning):
    deClient.SetHWROI(0, 0, hwSizeX, hwSizeY)
    deClient.SetProperty(propertyName.PROP_BINNING_X, swBinning)
    deClient.SetProperty(propertyName.PROP_BINNING_Y, swBinning)
    deClient.SetProperty(propertyName.PROP_HARDWARE_BINNING_X, hwBinning)


# Function to be tested
def testImageSize(hwSizeX, hwSizeY, swBinning, hwBinning):
    setProperties(hwSizeX, hwSizeY, swBinning, hwBinning)
    imageSizeX = deClient.GetProperty(propertyName.PROP_IMAGE_SIZE_X_PIXELS)
    imageSizeY = deClient.GetProperty(propertyName.PROP_IMAGE_SIZE_Y_PIXELS)
    return func.compare2Value(
        (hwSizeX / swBinning / hwBinning, hwSizeY / swBinning / hwBinning),
        (imageSizeX, imageSizeY),
        "Image Size: ",
    )


def testSwBinningAutoChange(hwSizeX, hwSizeY, swBinning, hwBinning):
    setProperties(hwSizeX, hwSizeY, swBinning, hwBinning)
    swBinningX = deClient.GetProperty(propertyName.PROP_BINNING_X)
    hwRoiSizeX = deClient.GetProperty(propertyName.PROP_HARDWARE_ROI_SIZE_X)
    return func.compare2Value(swBinningX, hwRoiSizeX / hwBinning, "SW Binning: ")


def testShape(hwSizeX, hwSizeY, swBinning, hwBinning):
    setProperties(hwSizeX, hwSizeY, swBinning, hwBinning)
    deClient.StartAcquisition()

    hardwareROISizeX = deClient.GetProperty(propertyName.PROP_HARDWARE_ROI_SIZE_X)
    hardwareROISizeY = deClient.GetProperty(propertyName.PROP_HARDWARE_ROI_SIZE_Y)

    image = deClient.GetResult(DEAPI.FrameType.SUMTOTAL, DEAPI.PixelFormat.UINT16)[0]
    return func.compare2Value(
        image.shape,
        (
            hardwareROISizeX / swBinning / hwBinning,
            hardwareROISizeY / swBinning / hwBinning,
        ),
        "Image Shape: ",
    )


# Unit test
class TestSwHwBinning(unittest.TestCase):

    def testImageSizeWhenbin1(self):
        self.assertTrue(testImageSize(256, 256, 1, 1))

    def testImageSizeWhenBin2(self):
        self.assertTrue(testImageSize(512, 512, 2, 2))

    def testSwBinningAutoChange1(self):
        self.assertTrue(testSwBinningAutoChange(1024, 1024, 1024, 2))

    def testSwBinningAutoChange2(self):
        self.assertTrue(testSwBinningAutoChange(512, 512, 512, 2))

    def testShapeWhenBin1(self):
        self.assertTrue(testShape(1024, 1024, 2, 1))

    def testShapeWhenBin2(self):
        self.assertTrue(testShape(512, 512, 2, 1))


if __name__ == "__main__":
    scriptName = os.path.basename(__file__)
    func.writeLogFile(TestSwHwBinning, scriptName)

    # Reset stdout to the console
    sys.stdout = sys.__stdout__

    # Always ensure that the properties are reset
    for key, value in defaultProperties.items():
        deClient.SetProperty(key, value)
    deClient.Disconnect()
    print("Disconnected from the camera and properties reset.")
