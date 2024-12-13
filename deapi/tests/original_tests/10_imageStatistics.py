import sys
import unittest
import deapi as DEAPI
from deapi.tests.original_tests import func, propertyName


# Total e- = e-/pix * ROI Size
# image->m_stats.physicalPixels = m_params.hw_frame.w * m_params.hw_frame.h;
# image->m_stats.frameCount = static_cast<int>(image->GetFrameCount());
# image->m_stats.e = image->m_stats.eppix * static_cast<float>(image->m_stats.physicalPixels);
# -> Total e- = e-/pix * RoiSizeX * RoiSizeY
# image->m_stats.eppix = image->m_stats.eppixpf * static_cast<float>(image->m_stats.frameCount);
# -> e-/pix = e-/pix/frame * framCount
# image->m_stats.eppixps = image->m_stats.eppixpf * m_params.GetFps();
# -> e-/pix/s = e-/pix/frame * Fps
# image->m_stats.eps = image->m_stats.eppixps * static_cast<float>(image->m_stats.physicalPixels);
# -> e-/s = e-/pix/s * RoiSizeX * RoiSizeY
# float angstromsSquared = 100.0f * m_params.m_specimenPixelNmX * m_params.m_specimenPixelNmY / (static_cast<float>(m_params.sw_binning.w) * static_cast<float>(m_params.sw_binning.h));
# image->m_stats.epa2 = image->m_stats.eppix / angstromsSquared;
# -> e-/a^2 = e-/pix / angstromsSquared
# HWSize: 1024*1024 # FPS: 10 # Processing mode: Integrating # Correction mode: Dark

deClient = DEAPI.Client()
deClient.Connect()
cameras = deClient.ListCameras()
camera = cameras[0]

serverVersion = deClient.GetProperty(propertyName.PROP_SERVER_SOFTWARE_VERSION)
cameraName = deClient.GetProperty(propertyName.PROP_CAMERA_NAME)
print(f"Camera Name: {cameraName}, Server Software Version: {serverVersion}")

# Store default properties in a dictionary
defaultProperties = {
    propertyName.PROP_TEST_PATTERN: deClient.GetProperty(
        propertyName.PROP_TEST_PATTERN
    ),
    propertyName.PROP_INSTRUMENT_CLIENT_ADDRESS: deClient.GetProperty(
        propertyName.PROP_INSTRUMENT_CLIENT_ADDRESS
    ),
    propertyName.PROP_INSTRUMENT_PROJECT_MAGNIFICATION: deClient.GetProperty(
        propertyName.PROP_INSTRUMENT_PROJECT_MAGNIFICATION
    ),
    propertyName.PROP_INSTRUMENT_ACCEL_VOLTAGE: deClient.GetProperty(
        propertyName.PROP_INSTRUMENT_ACCEL_VOLTAGE
    ),
    propertyName.PROP_HARDWARE_ROI_SIZE_X: deClient.GetProperty(
        propertyName.PROP_HARDWARE_ROI_SIZE_X
    ),
    propertyName.PROP_HARDWARE_ROI_SIZE_X: deClient.GetProperty(
        propertyName.PROP_HARDWARE_ROI_SIZE_X
    ),
    propertyName.PROP_FRAMES_PER_SECOND: deClient.GetProperty(
        propertyName.PROP_FRAMES_PER_SECOND
    ),
    propertyName.PROP_FRAME_COUNT: deClient.GetProperty(propertyName.PROP_FRAME_COUNT),
    propertyName.PROP_AUTOSAVE_MOVIE: deClient.GetProperty(
        propertyName.PROP_AUTOSAVE_MOVIE
    ),
    propertyName.PROP_IMAGE_PROCESSING_MODE: deClient.GetProperty(
        propertyName.PROP_IMAGE_PROCESSING_MODE
    ),
    propertyName.PROP_IMAGE_PROCESSING_FLATFIELD_CORRECTION: deClient.GetProperty(
        propertyName.PROP_IMAGE_PROCESSING_FLATFIELD_CORRECTION
    ),
    propertyName.PROP_BINNING_X: deClient.GetProperty(propertyName.PROP_BINNING_X),
    propertyName.PROP_BINNING_Y: deClient.GetProperty(propertyName.PROP_BINNING_Y),
}

testPattern = "SW Constant 400"
instrumentProjectMagnification = 2000
instrumentAcceleratingVoltageV = 80000
hwRoiSizeX = 1024
hwRoiSizeY = 1024
fps = 10
numPrecision = 6
frameCount = 1

deClient.SetCurrentCamera(camera)
# deClient.SetProperty("Test Pattern", testPattern)
deClient.SetProperty(propertyName.PROP_INSTRUMENT_CLIENT_ADDRESS, "Manual")
deClient.SetProperty(
    propertyName.PROP_INSTRUMENT_PROJECT_MAGNIFICATION, instrumentProjectMagnification
)
deClient.SetProperty(
    propertyName.PROP_INSTRUMENT_ACCEL_VOLTAGE, instrumentAcceleratingVoltageV
)
deClient.SetProperty(propertyName.PROP_HARDWARE_ROI_SIZE_X, hwRoiSizeX)
deClient.SetProperty(propertyName.PROP_HARDWARE_ROI_SIZE_Y, hwRoiSizeY)
deClient.SetProperty(propertyName.PROP_FRAMES_PER_SECOND, fps)
deClient.SetProperty(propertyName.PROP_AUTOSAVE_MOVIE, "Save")
deClient.SetProperty(propertyName.PROP_FRAME_COUNT, frameCount)
hwWidth = deClient.GetProperty(propertyName.PROP_HARDWARE_FRAME_SIZE_X)
hwHeight = deClient.GetProperty(propertyName.PROP_HARDWARE_FRAME_SIZE_Y)
frameCount = deClient.GetProperty(propertyName.PROP_FRAME_COUNT)
fps = deClient.GetProperty(propertyName.PROP_FRAMES_PER_SECOND)
specimenPixelXns = deClient.GetProperty(
    propertyName.PROP_SPECIMEN_PIXEL_SIZE_X_NANOMETERS
)
specimenPixelYns = deClient.GetProperty(
    propertyName.PROP_SPECIMEN_PIXEL_SIZE_Y_NANOMETERS
)
swBinX = deClient.GetProperty(propertyName.PROP_BINNING_X)
swBinY = deClient.GetProperty(propertyName.PROP_BINNING_Y)
numPhysicalPixels = hwWidth * hwHeight
attributes = DEAPI.Attributes()
pixelFormat = DEAPI.PixelFormat
frameType = DEAPI.FrameType


class Stats:
    def __init__(self):
        self.eppix = 0
        self.eppixps = 0
        self.eps = 0
        self.epa2 = 0

    def UpdateStats(
        self,
        eppixpf,
        frameCount,
        fps,
        numPhysicalPixels,
        specimenPixelXns,
        specimenPixelYns,
        swBinX,
        swBinY,
    ):
        self.eppix = eppixpf * frameCount  # -> e-/pix = e-/pix/frame * framCount
        self.eppixps = eppixpf * fps  # -> e-/pix/s = e-/pix/frame * Fps
        self.eps = (
            self.eppixps * numPhysicalPixels
        )  # -> e-/s = e-/pix/s * RoiSizeX * RoiSizeY
        angstromsSquared = (
            100.0 * specimenPixelXns * specimenPixelYns / (swBinX * swBinY)
        )
        self.epa2 = (
            self.eppix / angstromsSquared
        )  # -> e-/a^2 = e-/pix / angstromsSquared


def statisticsValueCheck(imageProcessingMode, correctionMode):
    deClient.SetProperty(propertyName.PROP_IMAGE_PROCESSING_MODE, imageProcessingMode)
    deClient.SetProperty(
        propertyName.PROP_IMAGE_PROCESSING_FLATFIELD_CORRECTION, correctionMode
    )
    deClient.SetProperty(propertyName.PROP_BINNING_X, swBinX)
    deClient.SetProperty(propertyName.PROP_BINNING_Y, swBinY)

    deClient.StartAcquisition()
    stats = Stats()
    image = deClient.GetResult(frameType.SUMTOTAL, pixelFormat.AUTO, attributes)

    stats.UpdateStats(
        attributes.eppixpf,
        frameCount,
        fps,
        numPhysicalPixels,
        specimenPixelXns,
        specimenPixelYns,
        swBinX,
        swBinY,
    )
    print(f"imagemean: {attributes.imageMean}")
    print(stats.eppix)
    print(stats.epa2)
    # Sometimes the float number are not equal due to the
    func.compare2FloatValue(stats.eppix, attributes.eppix, numPrecision, "e-/pix")
    func.compare2FloatValue(stats.eppixps, attributes.eppixps, numPrecision, "e-/pix/s")
    func.compare2FloatValue(stats.eps, attributes.eps, numPrecision, "e-/s")
    func.compare2FloatValue(stats.epa2, attributes.epa2, numPrecision, "e-/a^2")


def compareBin1Bin2(imageProcessingMode, correctionMode, swBinningFactor):
    deClient.SetProperty(propertyName.PROP_IMAGE_PROCESSING_MODE, imageProcessingMode)
    deClient.SetProperty(
        propertyName.PROP_IMAGE_PROCESSING_FLATFIELD_CORRECTION, correctionMode
    )

    deClient.SetProperty(propertyName.PROP_BINNING_X, 1)
    deClient.SetProperty(propertyName.PROP_BINNING_Y, 1)
    deClient.StartAcquisition()
    statsBin1 = Stats()

    image = deClient.GetResult(frameType.SUMTOTAL, pixelFormat.AUTO, attributes)
    statsBin1.UpdateStats(
        attributes.eppixpf,
        frameCount,
        fps,
        numPhysicalPixels,
        specimenPixelXns,
        specimenPixelYns,
        swBinX,
        swBinY,
    )

    deClient.SetProperty(propertyName.PROP_BINNING_X, swBinningFactor)
    deClient.SetProperty(propertyName.PROP_BINNING_Y, swBinningFactor)
    deClient.StartAcquisition()
    statsBin2 = Stats()

    image = deClient.GetResult(frameType.SUMTOTAL, pixelFormat.AUTO, attributes)
    statsBin2.UpdateStats(
        attributes.eppixpf,
        frameCount,
        fps,
        numPhysicalPixels,
        specimenPixelXns,
        specimenPixelYns,
        swBinX,
        swBinY,
    )

    func.compare2FloatValue(statsBin1.eppix, statsBin2.eppix, numPrecision, "e-/pix")
    func.compare2FloatValue(
        statsBin1.eppixps, statsBin2.eppixps, numPrecision, "e-/pix/s"
    )
    func.compare2FloatValue(statsBin1.eps, statsBin2.eps, numPrecision, "e-/s")
    func.compare2FloatValue(statsBin1.epa2, statsBin2.epa2, numPrecision, "e-/a^2")


class TestPatternPixelValues(unittest.TestCase):
    def testImageStatisticsTest1(self):
        self.assertTrue(
            statisticsValueCheck(
                imageProcessingMode="Integrating", correctionMode="Dark"
            )
        )

    def testImageStatisticsTest2(self):
        self.assertTrue(
            compareBin1Bin2(
                imageProcessingMode="Integrating",
                correctionMode="Dark",
                swBinningFactor=2,
            )
        )


if __name__ == "__main__":
    try:
        unittest.main()
    finally:
        # Always ensure that the properties are reset
        for key, value in defaultProperties.items():
            deClient.SetProperty(key, value)
        deClient.Disconnect()
        print("Disconnected from the camera and properties reset.")
