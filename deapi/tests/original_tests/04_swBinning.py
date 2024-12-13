import unittest
import sys
import os
from time import sleep

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
    propertyName.PROP_FRAMES_PER_SECOND: deClient.GetProperty(
        propertyName.PROP_FRAMES_PER_SECOND
    ),
    propertyName.PROP_HARDWARE_BINNING_X: deClient.GetProperty(
        propertyName.PROP_HARDWARE_BINNING_X
    ),
    propertyName.PROP_HARDWARE_BINNING_Y: deClient.GetProperty(
        propertyName.PROP_HARDWARE_BINNING_Y
    ),
}


hwBinningX = 1
hwBinningY = 1
frameCount = 1
testPattern = "Sequence"
attributes = DEAPI.Attributes()
pixelFormat = DEAPI.PixelFormat
frameType = DEAPI.FrameType

deClient.SetProperty(propertyName.PROP_FRAME_COUNT, frameCount)
deClient.SetProperty(propertyName.PROP_HARDWARE_BINNING_X, hwBinningX)
deClient.SetProperty(propertyName.PROP_HARDWARE_BINNING_Y, hwBinningY)


def setProperties(hwSizeX, hwSizeY, binningX, binningY):
    deClient.SetHWROI(0, 0, hwSizeX, hwSizeY)
    deClient.SetProperty(propertyName.PROP_BINNING_X, binningX)
    deClient.SetProperty(propertyName.PROP_BINNING_Y, binningY)


# Function to be tested
def ImageSize(hwSizeX, hwSizeY, binningX, binningY):

    setProperties(hwSizeX, hwSizeY, binningX, binningY)
    imageSizeX = deClient.GetProperty(propertyName.PROP_IMAGE_SIZE_X_PIXELS)
    imageSizeY = deClient.GetProperty(propertyName.PROP_IMAGE_SIZE_Y_PIXELS)

    return func.compare2Value(
        (hwSizeX / binningX, hwSizeY / binningY),
        (imageSizeX, imageSizeY),
        "Image Size: ",
    )


def Shape(hwSizeX, hwSizeY, binningX, binningY):

    setProperties(hwSizeX, hwSizeY, binningX, binningY)
    deClient.StartAcquisition()
    while deClient.acquiring:
        sleep(0.1)
    hardwareROISizeX = deClient.GetProperty(propertyName.PROP_HARDWARE_ROI_SIZE_X)
    hardwareROISizeY = deClient.GetProperty(propertyName.PROP_HARDWARE_ROI_SIZE_Y)
    image = deClient.GetResult(DEAPI.FrameType.SUMTOTAL, DEAPI.PixelFormat.UINT16)[0]

    return func.compare2Value(
        image.shape,
        (hardwareROISizeX / binningX, hardwareROISizeY / binningY),
        "Image Shape: ",
    )


def minMaxCheckForBinning(hwSizeX, hwSizeY, binningX, binningY):
    setProperties(hwSizeX, hwSizeY, binningX, binningY)
    deClient.SetProperty(propertyName.PROP_TEST_PATTERN, testPattern)
    deClient.StartAcquisition()
    while deClient.acquiring:
        sleep(0.1)
    image = deClient.GetResult(frameType.SUMTOTAL, pixelFormat.AUTO, attributes)

    return func.compare2Value(0, attributes.imageMin, "Min: ") and func.compare2Value(
        1023, attributes.imageMax, "Max: "
    )


# Unit test
class TestSwBinning(unittest.TestCase):

    def testImageSizeWhenBin1(self):
        self.assertTrue(ImageSize(256, 256, 1, 1))

    def testImageSizeWhenBin2(self):
        self.assertTrue(ImageSize(512, 512, 2, 2))

    def testImageSizeWhenBin3(self):
        self.assertTrue(ImageSize(1024, 1024, 4, 4))

    def testImageSizeWhenBin4(self):
        self.assertTrue(ImageSize(1024, 1024, 8, 8))

    def testShapeWhenBin1(self):
        self.assertTrue(Shape(256, 256, 1, 1))

    def testShapeWhenBin2(self):
        self.assertTrue(Shape(512, 512, 2, 2))

    def testShapeWhenBin3(self):
        self.assertTrue(Shape(1024, 1024, 4, 4))

    def testShapeWhenBin4(self):
        self.assertTrue(Shape(1024, 1024, 8, 8))

    def testMinMaxCheckForBinning1(self):
        self.assertTrue(minMaxCheckForBinning(1024, 1024, 1024, 1))


if __name__ == "__main__":
    scriptName = os.path.basename(__file__)
    func.writeLogFile(TestSwBinning, scriptName)

    # Reset stdout to the console
    sys.stdout = sys.__stdout__

    # Always ensure that the properties are reset
    for key, value in defaultProperties.items():
        deClient.SetProperty(key, value)
    deClient.Disconnect()
    print("Disconnected from the camera and properties reset.")
