import sys
import unittest
import random
import mrcfile
import numpy as np

import os
import deapi as DEAPI
from deapi.tests.original_tests import func, propertyName

deClient = DEAPI.Client()
# Connect to the Server
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
    propertyName.PROP_FRAMES_PER_SECOND: deClient.GetProperty(
        propertyName.PROP_FRAMES_PER_SECOND
    ),
    propertyName.PROP_IMAGE_PROCESSING_MODE: deClient.GetProperty(
        propertyName.PROP_IMAGE_PROCESSING_MODE
    ),
    propertyName.PROP_AUTOSAVE_FINAL_IMAGE: deClient.GetProperty(
        propertyName.PROP_AUTOSAVE_FINAL_IMAGE
    ),
    propertyName.PROP_IMAGE_PROCESSING_FLATFIELD_CORRECTION: deClient.GetProperty(
        propertyName.PROP_IMAGE_PROCESSING_FLATFIELD_CORRECTION
    ),
}

# Set default:
# Set "Check TEM-Channel" to "Off"
deClient.SetProperty(propertyName.PROP_CHECK_TEM_CHANNEL, "Off")
# Set "SW Constant 10"
pixelValue = 10
deClient.SetProperty(propertyName.PROP_TEST_PATTERN, "SW Constant 10")

frameCount = 1
hwSizeX = 1024
hwSizeY = 1024
hwBinningX = 1
hwBinningY = 1
fps = 10
binningX = 2
binningY = 2
frame_type = DEAPI.FrameType.SUMTOTAL

deClient.SetHWROI(0, 0, hwSizeX, hwSizeY)
deClient.SetProperty(propertyName.PROP_HARDWARE_BINNING_X, hwBinningX)
deClient.SetProperty(propertyName.PROP_HARDWARE_BINNING_Y, hwBinningY)
deClient.SetProperty(propertyName.PROP_BINNING_X, binningX)
deClient.SetProperty(propertyName.PROP_BINNING_Y, binningY)
deClient.SetProperty(propertyName.PROP_FRAMES_PER_SECOND, fps)
deClient.SetProperty(propertyName.PROP_FRAME_COUNT, frameCount)
deClient.SetProperty(propertyName.PROP_IMAGE_PROCESSING_MODE, "Integrating")
deClient.SetProperty(propertyName.PROP_AUTOSAVE_FINAL_IMAGE, "Save")
deClient.SetProperty(propertyName.PROP_IMAGE_PROCESSING_FLATFIELD_CORRECTION, "None")


def patternTest(binningMethod, expectedValue):
    deClient.SetProperty(propertyName.PROP_BINNING_METHOD, binningMethod)
    deClient.StartAcquisition()
    image = deClient.GetResult(frame_type, DEAPI.PixelFormat.UINT16)[0]
    fName = (
        deClient.GetProperty("Autosave Directory")
        + "\\"
        + deClient.GetProperty("Dataset Name")
        + "_final.mrc"
    )

    with mrcfile.open(fName, permissive=True) as mrc:
        # Read the data
        data = mrc.data
        mrcData = data[0]

        # Define the dimensions of the image
        height, width = mrcData.shape

        # Generate a list of random coordinates
        numCoords = 5  # Number of random coordinates
        values = {}
        for _ in range(numCoords):
            randX = random.randint(0, width - 1)
            randY = random.randint(0, height - 1)
            values[(randX, randY)] = mrcData[randY, randX]

        # Print the pixel values
        for coord, value in values.items():
            if value != expectedValue:
                print(
                    f"Error: Pixel Coordinates {coord} : value {value} expectValue {expectedValue}"
                )
                return False

        # Print the mean of pixel values
        meanValue = np.mean(mrcData)
        if meanValue != expectedValue:
            print(f"Error: mean value : {meanValue} expectValue {expectedValue}")
            return False

        return True


class TestPatternPixelValues(unittest.TestCase):

    def testPatternTest1(self):
        self.assertTrue(patternTest("Sum", pixelValue * binningX * binningY))

    def testPatternTest2(self):
        self.assertTrue(patternTest("Average", pixelValue))


if __name__ == "__main__":
    scriptName = os.path.basename(__file__)
    func.writeLogFile(TestPatternPixelValues, scriptName)

    # Reset stdout to the console
    sys.stdout = sys.__stdout__

    # Always ensure that the properties are reset
    for key, value in defaultProperties.items():
        deClient.SetProperty(key, value)
    deClient.Disconnect()
    print("Disconnected from the camera and properties reset.")
