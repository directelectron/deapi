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
    propertyName.PROP_FRAMES_PER_SECOND: deClient.GetProperty(
        propertyName.PROP_FRAMES_PER_SECOND
    ),
    propertyName.PROP_HARDWARE_ROI_SIZE_X: deClient.GetProperty(
        propertyName.PROP_HARDWARE_ROI_SIZE_X
    ),
    propertyName.PROP_HARDWARE_ROI_SIZE_X: deClient.GetProperty(
        propertyName.PROP_HARDWARE_ROI_SIZE_Y
    ),
    propertyName.PROP_EXPOSURE_TIME_SECONDS: deClient.GetProperty(
        propertyName.PROP_EXPOSURE_TIME_SECONDS
    ),
}


def setProperties(fps, hwSizeX, hwSizeY, exTime=None):
    deClient.SetProperty(propertyName.PROP_HARDWARE_ROI_SIZE_X, hwSizeX)
    deClient.SetProperty(propertyName.PROP_HARDWARE_ROI_SIZE_Y, hwSizeY)
    deClient.SetProperty(propertyName.PROP_FRAMES_PER_SECOND, fps)
    if exTime is not None:
        deClient.SetProperty(propertyName.PROP_EXPOSURE_TIME_SECONDS, exTime)


# Function to be tested
def TestFps(fps, hwSizeX, hwSizeY):
    setProperties(fps, hwSizeX, hwSizeY)
    value = int(deClient.GetProperty(propertyName.PROP_FRAMES_PER_SECOND))
    return func.compare2Value(fps, value, "Fps: ")


def TestMaxFps(fps, hwSizeX, hwSizeY):
    if not cameraName == "DESim":
        setProperties(fps, hwSizeX, hwSizeY)
        value = deClient.GetProperty(propertyName.PROP_FRAMES_PER_SECOND)
        maxFps = deClient.GetProperty(propertyName.PROP_FRAMES_PER_SECOND_MAX)
        return func.compare2Value(maxFps, value, "MaxFps: ")
    else:
        return True


def TestFrameCount(fps, hwSizeX, hwSizeY, exTime):
    setProperties(fps, hwSizeX, hwSizeY, exTime)
    frameCount = deClient.GetProperty(propertyName.PROP_FRAME_COUNT)
    return func.compare2Value(fps * exTime, frameCount, "Frame Count: ")


class testFPS(unittest.TestCase):
    # Set fps: 25
    def testFpsTest1(self):
        self.assertTrue(TestFps(25, 1024, 1024))

    # Set fps: 50
    def testFpsTest2(self):
        self.assertTrue(TestFps(50, 1024, 1024))

    # Set max fps: 99999 and check if it will auto change to the correct max fps
    def testMaxFpsTest1(self):
        self.assertTrue(TestMaxFps(99999, 1024, 1024))

    def testMaxFpsTest2(self):
        self.assertTrue(TestMaxFps(99999, 512, 512))

    # Check Frame Count in different exposure time and fps
    def testFpsAndExTimeTest1(self):
        self.assertTrue(TestFrameCount(30, 1024, 1024, 5))

    def testFpsAndExTimeTest2(self):
        self.assertTrue(TestFrameCount(30, 512, 512, 5))


if __name__ == "__main__":
    scriptName = os.path.basename(__file__)
    func.writeLogFile(testFPS, scriptName)

    # Reset stdout to the console
    sys.stdout = sys.__stdout__

    # Always ensure that the properties are reset
    for key, value in defaultProperties.items():
        deClient.SetProperty(key, value)
    deClient.Disconnect()
    print("Disconnected from the camera and properties reset.")
