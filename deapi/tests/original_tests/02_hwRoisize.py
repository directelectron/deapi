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
    propertyName.PROP_HARDWARE_ROI_SIZE_X: deClient.GetProperty(
        propertyName.PROP_HARDWARE_ROI_SIZE_X
    ),
    propertyName.PROP_HARDWARE_ROI_SIZE_Y: deClient.GetProperty(
        propertyName.PROP_HARDWARE_ROI_SIZE_Y
    ),
    propertyName.PROP_EXPOSURE_TIME_SECONDS: deClient.GetProperty(
        propertyName.PROP_EXPOSURE_TIME_SECONDS
    ),
}

hwBinningX = 1
hwBinningY = 1
frameCount = 1

deClient.SetProperty(propertyName.PROP_FRAME_COUNT, frameCount)
deClient.SetProperty(propertyName.PROP_HARDWARE_BINNING_X, hwBinningX)
deClient.SetProperty(propertyName.PROP_HARDWARE_BINNING_Y, hwBinningY)


# Function to be tested
def HwROISize(hwSizeX, hwSizeY):
    deClient.SetHWROI(0, 0, hwSizeX, hwSizeY)
    hwROISizeX = deClient.GetProperty(propertyName.PROP_HARDWARE_ROI_SIZE_X)
    hwROISizeY = deClient.GetProperty(propertyName.PROP_HARDWARE_ROI_SIZE_Y)
    return func.compare2Value(
        (hwSizeX, hwSizeY), (hwROISizeX, hwROISizeY), "Hw Roi Size: "
    )


def HwFrameSize(hwSizeX, hwSizeY):
    deClient.SetHWROI(0, 0, hwSizeX, hwSizeY)
    hardwareFrameSizeX = deClient.GetProperty(propertyName.PROP_HARDWARE_FRAME_SIZE_X)
    hardwareFrameSizeY = deClient.GetProperty(propertyName.PROP_HARDWARE_FRAME_SIZE_Y)
    return func.compare2Value(
        (hwSizeX, hwSizeY), (hardwareFrameSizeX, hardwareFrameSizeY), "Hw Frame Size: "
    )


def ImageSize(hwSizeX, hwSizeY):
    deClient.SetHWROI(0, 0, hwSizeX, hwSizeY)
    imageSizeX = deClient.GetProperty(propertyName.PROP_IMAGE_SIZE_X_PIXELS)
    imageSizeY = deClient.GetProperty(propertyName.PROP_IMAGE_SIZE_Y_PIXELS)
    return func.compare2Value(
        (hwSizeX, hwSizeY), (imageSizeX, imageSizeY), "Image Size: "
    )


def CropSize(hwSizeX, hwSizeY):
    deClient.SetHWROI(0, 0, hwSizeX, hwSizeY)
    cropSizeX = deClient.GetProperty(propertyName.PROP_CROP_SIZE_X)
    cropSizeY = deClient.GetProperty(propertyName.PROP_CROP_SIZE_Y)
    return func.compare2Value((hwSizeX, hwSizeY), (cropSizeX, cropSizeY), "Crop Size: ")


def HwOffsetSize(hwOffsetSizeX, hwOffsetSizeY, hwSizeX, hwSizeY):
    deClient.SetHWROI(hwOffsetSizeX, hwOffsetSizeY, hwSizeX, hwSizeY)
    checkHwOffsetX = deClient.GetProperty(propertyName.PROP_HARDWARE_ROI_OFFSET_X)
    checkHwOffsetY = deClient.GetProperty(propertyName.PROP_HARDWARE_ROI_OFFSET_Y)
    hwFrameX = deClient.GetProperty(propertyName.PROP_HARDWARE_FRAME_SIZE_X)
    hwFrameY = deClient.GetProperty(propertyName.PROP_HARDWARE_FRAME_SIZE_Y)
    return func.compare2Value(
        (hwOffsetSizeX, hwOffsetSizeY),
        (checkHwOffsetX, checkHwOffsetY),
        "Hw Offset Size: ",
    ) and func.compare2Value(
        (checkHwOffsetX, checkHwOffsetY),
        (hwSizeX - hwFrameX, hwSizeY - hwFrameY),
        "Hw Offset Size: ",
    )


def Shape(hwOffsetX, hwOffsetY, hwSizeX, hwSizeY):
    deClient.SetHWROI(hwOffsetX, hwOffsetY, hwSizeX, hwSizeY)
    deClient.StartAcquisition()

    hwROISizeX = deClient.GetProperty(propertyName.PROP_HARDWARE_ROI_SIZE_X)
    hwROISizeY = deClient.GetProperty(propertyName.PROP_HARDWARE_ROI_SIZE_Y)

    image = deClient.GetResult(DEAPI.FrameType.SUMTOTAL, DEAPI.PixelFormat.UINT16)[0]

    return func.compare2Value(image.shape, (hwROISizeX, hwROISizeY), "Shape Size: ")


# Unit test
class TestHwROISize(unittest.TestCase):

    def testHwROISize1(self):
        self.assertTrue(HwROISize(1024, 1024))

    def testHwROISize2(self):
        self.assertTrue(HwROISize(512, 512))

    def testHwROIFrameSize1(self):
        self.assertTrue(HwFrameSize(1024, 1024))

    def testHwROIFrameSize2(self):
        self.assertTrue(HwFrameSize(512, 512))

    def testImageSize1(self):
        self.assertTrue(ImageSize(1024, 1024))

    def testImageSize2(self):
        self.assertTrue(ImageSize(256, 256))

    def testCropSize1(self):
        self.assertTrue(CropSize(512, 512))

    def testCropSize2(self):
        self.assertTrue(CropSize(64, 64))

    def testHwOffsetSize1(self):
        self.assertTrue(HwOffsetSize(64, 64, 1024, 1024))

    def testHwOffsetSize2(self):
        self.assertTrue(HwOffsetSize(32, 32, 1024, 1024))

    def testTestShape1(self):
        self.assertTrue(Shape(0, 0, 512, 512))

    def testTestShape2(self):
        self.assertTrue(Shape(16, 16, 1024, 1024))


if __name__ == "__main__":
    scriptName = os.path.basename(__file__)
    func.writeLogFile(TestHwROISize, scriptName)

    # Reset stdout to the console
    sys.stdout = sys.__stdout__

    # Always ensure that the properties are reset
    for key, value in defaultProperties.items():
        deClient.SetProperty(key, value)
    deClient.Disconnect()
    print("Disconnected from the camera and properties reset.")
