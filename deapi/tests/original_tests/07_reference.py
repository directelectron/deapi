import unittest
import sys
from time import sleep
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
    propertyName.PROP_EXPOSURE_TIME_SECONDS: deClient.GetProperty(
        propertyName.PROP_EXPOSURE_TIME_SECONDS
    ),
    propertyName.PROP_FRAMES_PER_SECOND: deClient.GetProperty(
        propertyName.PROP_FRAMES_PER_SECOND
    ),
}

fps = 10
exTime = 1
acquisitions = 10
frameCount = 1
deClient.SetProperty(propertyName.PROP_FRAME_COUNT, frameCount)


def TakeDarkRef():

    deClient.SetProperty(propertyName.PROP_EXPOSURE_MODE, "Dark")
    deClient.SetProperty(propertyName.PROP_FRAMES_PER_SECOND, fps)
    deClient.SetProperty(propertyName.PROP_EXPOSURE_TIME_SECONDS, exTime)
    deClient.StartAcquisition(acquisitions)

    for i in range(10):
        while 10 - i <= int(
            deClient.GetProperty(propertyName.PROP_REMAINING_NUMBER_OF_ACQUISITIONS)
        ):
            sleep(1)
    darkReference = deClient.GetProperty(propertyName.PROP_REFERENCE_DARK)
    return func.compare2Value(darkReference[:5], "Valid", "Dark Reference: ")


def TakeGainRef():
    deClient.SetProperty(propertyName.PROP_EXPOSURE_MODE, "Gain")
    deClient.SetProperty(propertyName.PROP_FRAMES_PER_SECOND, fps)
    deClient.SetProperty(propertyName.PROP_EXPOSURE_TIME_SECONDS, exTime)
    deClient.StartAcquisition(acquisitions)

    for i in range(10):
        while 10 - i <= int(
            deClient.GetProperty(propertyName.PROP_REMAINING_NUMBER_OF_ACQUISITIONS)
        ):
            sleep(1)

    gainReference = deClient.GetProperty(propertyName.PROP_REFERENCE_GAIN)
    return func.compare2Value(gainReference[:5], "Valid", "Gain Reference: ")


# Unit test
class testRef(unittest.TestCase):
    # Set fps: 25
    def testDarkRef(self):
        self.assertTrue(TakeDarkRef())

    # Set fps: 50
    def testGainRed(self):
        self.assertTrue(TakeGainRef())


if __name__ == "__main__":
    scriptName = os.path.basename(__file__)
    func.writeLogFile(testRef, scriptName)

    # Reset stdout to the console
    sys.stdout = sys.__stdout__

    # Always ensure that the properties are reset
    for key, value in defaultProperties.items():
        deClient.SetProperty(key, value)
    deClient.Disconnect()
    print("Disconnected from the camera and properties reset.")
