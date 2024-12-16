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
print(f"Camera Name: {cameraName}, Server Software Version: {serverVersion}")

# Store default properties in a dictionary
defaultProperties = {
    propertyName.PROP_SCAN_ENABLE: deClient.GetProperty(propertyName.PROP_SCAN_ENABLE),
    propertyName.PROP_SCAN_ROI_ENABLE: deClient.GetProperty(
        propertyName.PROP_SCAN_ROI_ENABLE
    ),
    propertyName.PROP_SCAN_SIZE_X: deClient.GetProperty(propertyName.PROP_SCAN_SIZE_X),
    propertyName.PROP_SCAN_SIZE_Y: deClient.GetProperty(propertyName.PROP_SCAN_SIZE_Y),
    propertyName.PROP_SCAN_ROI_SIZE_X: deClient.GetProperty(
        propertyName.PROP_SCAN_ROI_SIZE_X
    ),
    propertyName.PROP_SCAN_ROI_SIZE_Y: deClient.GetProperty(
        propertyName.PROP_SCAN_ROI_SIZE_Y
    ),
    propertyName.PROP_SCAN_ROI_OFFSET_X: deClient.GetProperty(
        propertyName.PROP_SCAN_ROI_OFFSET_X
    ),
    propertyName.PROP_SCAN_ROI_OFFSET_Y: deClient.GetProperty(
        propertyName.PROP_SCAN_ROI_OFFSET_Y
    ),
}

ScanSizeX = 512
ScanSizeY = 512

deClient.SetProperty(propertyName.PROP_SCAN_ENABLE, "On")
deClient.SetProperty(propertyName.PROP_SCAN_ROI_ENABLE, "On")
deClient.SetProperty(propertyName.PROP_SCAN_SIZE_X, ScanSizeX)
deClient.SetProperty(propertyName.PROP_SCAN_SIZE_Y, ScanSizeY)


# Function to be tested
def testScanRoi(scanRoiSizeX, scanRoiSizeY):
    deClient.SetProperty(propertyName.PROP_SCAN_ROI_SIZE_X, scanRoiSizeX)
    deClient.SetProperty(propertyName.PROP_SCAN_ROI_SIZE_Y, scanRoiSizeY)
    scanPoint = deClient.GetProperty(propertyName.PROP_SCAN_POINTS)
    return func.compare2Value(scanPoint, scanRoiSizeX * scanRoiSizeY, "Scan Roi Size: ")


def testScanRoOffset(scanRoiSizeX, scanRoiSizeY, scanRoiOffsetX, scanRoiOffsetY):
    deClient.SetProperty(propertyName.PROP_SCAN_SIZE_X, scanRoiSizeX)
    deClient.SetProperty(propertyName.PROP_SCAN_SIZE_Y, scanRoiSizeY)
    deClient.SetProperty(propertyName.PROP_SCAN_ROI_OFFSET_X, scanRoiOffsetX)
    deClient.SetProperty(propertyName.PROP_SCAN_ROI_OFFSET_Y, scanRoiOffsetY)
    checkScanRoiOffsetX = deClient.GetProperty(propertyName.PROP_SCAN_ROI_OFFSET_X)
    checkScanRoiOffsetY = deClient.GetProperty(propertyName.PROP_SCAN_ROI_OFFSET_Y)
    checkScanRoiSizeX = deClient.GetProperty(propertyName.PROP_SCAN_ROI_SIZE_X)
    checkScanRoiSizeY = deClient.GetProperty(propertyName.PROP_SCAN_ROI_SIZE_Y)
    return func.compare2Value(
        (scanRoiOffsetX, scanRoiOffsetY),
        (checkScanRoiOffsetX, checkScanRoiOffsetY),
        "Scan Roi Offset: ",
    ) and func.compare2Value(
        (checkScanRoiSizeX, checkScanRoiSizeY),
        (scanRoiSizeX - checkScanRoiOffsetX, scanRoiSizeY - checkScanRoiOffsetY),
        "Scan Roi Size: ",
    )


# Unit test
class TestHwROISize(unittest.TestCase):

    def testScanRoi1(self):
        self.assertTrue(testScanRoi(64, 64))

    def testScanRoi2(self):
        self.assertTrue(testScanRoi(256, 256))

    def testScanRoiOffset1(self):
        self.assertTrue(testScanRoOffset(32, 32, 8, 8))

    def testScanRoiOffset2(self):
        self.assertTrue(testScanRoOffset(64, 64, 16, 16))


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
