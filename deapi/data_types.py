# File containing the data types used in the DE API
#
# Last update: 2024-08-07
# cfrancis@directelectron.com


from enum import Enum
from enum import IntEnum
from warnings import warn

class FrameType(Enum):
    NONE = 0
    AUTO = 1
    CRUDEFRAME = 2
    SINGLEFRAME_RAWLEVEL0 = 3
    SINGLEFRAME_RAWLEVEL1 = 4
    SINGLEFRAME_RAWLEVEL2 = 5
    SINGLEFRAME_RAWOFFCHIPCDS = 6
    SINGLEFRAME_INTEGRATED = 7
    SINGLEFRAME_COUNTED = 8
    SUMINTERMEDIATE = 9
    SUMTOTAL = 10
    CUMULATIVE = 11
    VIRTUAL_MASK0 = 12
    VIRTUAL_MASK1 = 13
    VIRTUAL_MASK2 = 14
    VIRTUAL_MASK3 = 15
    VIRTUAL_MASK4 = 16
    VIRTUAL_IMAGE0 = 17
    VIRTUAL_IMAGE1 = 18
    VIRTUAL_IMAGE2 = 19
    VIRTUAL_IMAGE3 = 20
    VIRTUAL_IMAGE4 = 21
    EXTERNAL_IMAGE1 = 22
    EXTERNAL_IMAGE2 = 23
    EXTERNAL_IMAGE3 = 24
    EXTERNAL_IMAGE4 = 25
    DEBUG_INPUT1 = 26
    DEBUG_INPUT2 = 27
    DEBUG_CENTROIDINGEVENTMOMENTSX = 28
    DEBUG_CENTROIDINGEVENTMOMENTSY = 29
    DEBUG_CENTROIDINGEVENTMOMENTSINTENSITY = 30
    DEBUG_CENTROIDINGEVENTLABELS = 31
    DEBUG_CENTROIDINGEVENTOTHERDATA = 32
    DEBUG_DEEPMINX = 33
    DEBUG_DEEPMINY = 34
    DEBUG_DEEPMAXX = 35
    DEBUG_DEEPMAXY = 36
    REFERENCE_DARKLEVEL0 = 37
    REFERENCE_DARKLEVEL1 = 38
    REFERENCE_DARKLEVEL2 = 39
    REFERENCE_DARKOFFCHIPCDS = 40
    REFERENCE_GAININTEGRATINGLEVEL0 = 41
    REFERENCE_GAININTEGRATINGLEVEL1 = 42
    REFERENCE_GAININTEGRATINGLEVEL2 = 43
    REFERENCE_GAINCOUNTING = 44
    REFERENCE_GAINFINALINTEGRATINGLEVEL0 = 45
    REFERENCE_GAINFINALCOUNTING = 46
    REFERENCE_BADPIXELS = 47
    REFERENCE_BADPIXELMAP = 48
    SUMTOTAL_MOTIONCORRECTED = 49
    SCAN_SUBSAMPLINGMASK = 50
    NUMBER_OF_OPTIONS = 51
    # deprecated frame type
    CRUDE_FRAME = 2  # for engineering testing        #Same as CRUDEFRAME
    SINGLE_FRAME_RAW_LEVEL0 = (
        3  # for engineering testing        #Same as SINGLEFRAME_RAWLEVEL0
    )
    SINGLE_FRAME_RAW_LEVEL1 = (
        4  # for engineering testing        #Same as SINGLEFRAME_RAWLEVEL1
    )
    SINGLE_FRAME_RAW_LEVEL2 = (
        5  # for engineering testing        #Same as SINGLEFRAME_RAWLEVEL2
    )
    SINGLE_FRAME_RAW_CDS = (
        6  # for engineering testing        #Same as SINGLEFRAME_RAWOFFCHIPCDS
    )
    SINGLE_FRAME_INTEGRATED = (
        7  # single integrated frame        #Same as SINGLEFRAME_INTEGRATED
    )
    SINGLE_FRAME_COUNTED = (
        8  # single counted frame           #same as SINGLEFRAME_COUNTED
    )
    MOVIE_INTEGRATED = 9  # fractionated integrated frame  #same as SUMINTERMEDIATE
    MOVIE_COUNTED = 9  # fractionated counted frame     #same as SUMINTERMEDIATE
    TOTAL_SUM_INTEGRATED = 10  # sum of all integrated frame    #same as SUMTOTAL
    TOTAL_SUM_COUNTED = 10  # sum of all counted frame       #same as SUMTOTAL
    CUMULATIVE_INTEGRATED = 11  # cumulative integrted frame     #same as CUMULATIVE
    CUMULATIVE_COUNTED = 11  # cumulative counted frame       #same as CUMULATIVE


class PixelFormat(Enum):
    UINT8 = 1  # 8-bit integer
    UINT16 = 5  # 16-bit integer
    FLOAT32 = 13  # 32-bit float
    AUTO = -1  # Automatically determined by the server


class DataType(Enum):
    DEUndef = -1
    DE8u = 1
    DE16u = 5
    DE16s = 7
    DE32f = 13


class MovieBufferStatus(Enum):
    UNKNOWN = 0
    FAILED = 1
    TIMEOUT = 3
    FINISHED = 4
    OK = 5


class ContrastStretchType(IntEnum):
    NONE = 0
    MANUAL = 1
    LINEAR = 2
    DIFFRACTION = 3
    THONRINGS = 4
    NATURAL = 5
    HIGHCONTRAST = 6
    WIDERANGE = 7


class Attributes:
    centerX = 0  # In:  x coordinate of the center of the original image to pan to
    centerY = 0  # In:  y coordinate of the center of the original image to pan to
    zoom = 1.0  # In:  zoom level on the returned image
    windowWidth = 0  # In:  Width of the returned image in pixels
    windowHeight = 0  # In:  Height of the returned image in pixels
    fft = False  # In:  request to return the FFT of the image
    linearStretch = False
    stretchType = (
        ContrastStretchType.LINEAR
    )  # In: Contrast Stretch type. It is Linear by default TODO: enum
    manualStretchMin = 0.0  # In: Manual Stretch Minimum is adjusted by the user when the contrast stretch type is Manual.
    manualStretchMax = 0.0  # In: Manual Stretch Maximum is adjusted by the user when the contrast stretch type is Manual.
    manualStretchGamma = 1.0  # In: Manual Stretch Gamma is adjusted by the user when the contrast stretch type is Manual.
    outlierPercentage = 2.0  # In:  Percentage of outlier pixels at each end of the image histogram to ignore during contrast stretching if linearStretch is true.
    buffered = False  # In:  Deprecated attribute, please use GetMovieBuffer to get all movie frames
    timeoutMsec = -1  # In:  Timeout in milliseconds for GetResult call.
    frameWidth = 0  # Out: Width of the processed image in pixels before panning and zooming. This matches the size of the saved images.
    frameHeight = 0  # Out: Height of the processed image in pixels before panning and zooming. This matches the size of the saved images.
    datasetName = None  # Out: Data set name that the retrieved frame belongs to. Each repeat of acquisition has its own unique dataset name. e.g. 20210902_00081
    acqIndex = 0  # Out: Zero-based acquisition index. Incremented after each repeat of acquisition, up to one less of the numberOfAcquisitions parameter of the StartAcquisition call
    acqFinished = False  # Out: Indicates whether the current acquisition is finished.
    imageIndex = 0  # Out: Zero-based index within the acquisition that the retrieved frame belongs to
    frameCount = 0  # Out: Number of frames summed up to make the returned image
    imageMin = 0  # Out: Minimum pixel value of the retrieved image.
    imageMax = 0  # Out: Maximum pixel value of the retrieved image.
    imageMean = 0  # Out: Mean pixel values of the retrieved image.
    imageStd = 0  # Out: Standard deviation of pixel values of the retrieved image.
    eppix = 0  # Out: The mean total electrons per pixel calculated for the acquisition.
    eps = 0  # Out: The mean total electrons per second over the entire readout area for the acquisition.
    eppixps = 0  # Out: The mean electrons per pixel per second calculated for the acquisition.
    epa2 = 0  # Out: The mean total electrons per square Angstrom calculated for the acquisition.
    eppixpf = (
        0  # Out: The mean electrons per pixel per frame calculated for the acquisition.
    )
    eppix_incident = 0  # Out: The incident mean total electrons per pixel calculated for the acquisition.
    eps_incident = 0  # Out: The incident mean total electrons per second over the entire readout area for the acquisition.
    eppixps_incident = 0  # Out: The incident mean electrons per pixel per second calculated for the acquisition.
    epa2_incident = 0  # Out: The incident mean total electrons per square Angstrom calculated for the acquisition.
    eppixpf_incident = 0  # Out: The incident mean electrons per pixel per frame calculated for the acquisition.
    underExposureRate = 0  # Out: Percentage of pixels under the Statistics - Underexposure Mark (percentage) property value.
    overExposureRate = 0  # Out: Percentage of pixels over the Statistics - Overexposure Mark (percentage) property value.
    timestamp = 0  # Out: Timestamp in seconds since the Unix epoch time when the frame arrived at the computer.
    autoStretchMin = (
        0.0  # Out: Auto Stretch Minimum is returned by getAsyncOutput in server.
    )
    autoStretchMax = (
        0.0  # Out: Auto Stretch Maximum is returned by getAsyncOutput in server.
    )
    autoStretchGamma = (
        1.0  # Out: Auto Stretch Gamma is returned by getAsyncOutput in server.
    )
    saturation = 0.0


class Histogram:
    min = 0.0  # In/Out: minimum histogram value, if min and max is set to the same value, or in trial of gain acquisition mode, the server will determine this value.
    max = 0.0  # In/Out: maximum histogram value, if min and max is set to the same value, or in trial of gain acquisition mode, the server will determine this value.
    upperMostLocalMaxima = 0  # In/Out: upper local max histogram value
    bins = (
        256  # In:     number of bins requested, 0 means histogram data is not requested
    )
    data = None  # Out:    buffer containing histogram data


class MovieBufferInfo:
    """
    Structure to hold information about the movie buffer

    Parameters
    ----------
    headerBytes : int
        Number of bytes in the header
    imageBufferBytes : int
        Number of bytes in the image buffer
    frameIndexStartPos : int
        Starting position of the frame index
    imageStartPos : int
        Starting position of the image
    imageW : int
        Width of the image
    imageH : int
        Height of the image
    framesInBuffer : int
        Number of frames in the buffer
    imageDataType : int
        Data type of the image
    """
    def __init__(self, headerBytes: int=0,
                 imageBufferBytes: int=0,
                 frameIndexStartPos: int=0,
                 imageStartPos: int=0,
                 imageW: int=0,
                 imageH: int=0,
                 framesInBuffer: int=0,
                 imageDataType: int = DataType.DEUndef):

        self.headerBytes = headerBytes
        self.imageBufferBytes = imageBufferBytes
        self.frameIndexStartPos = frameIndexStartPos
        self.imageStartPos = imageStartPos
        self.imageW = imageW
        self.imageH = imageH
        self.framesInBuffer = framesInBuffer
        self.imageDataType = imageDataType

    @property
    def total_bytes(self):
        return self.headerBytes + self.imageBufferBytes

    def to_buffer(self):
        return bytearray(self.total_bytes)


class PropertySpec:
    dataType = None  # "String"   | "Integer"  | "Float"
    valueType = None  # "ReadOnly" | "Set"      | "Range"       | "AllowAll"
    category = (
        None  # "Basic"    | "Advanced" | "Engineering" | "Deprecated" | Obsolete"
    )
    options = None  # List of options
    defaultValue = None  # default value
    currentValue = None  # current value


class PropertyCollection:
    """Class to interact with collections of properties in the DE API

    Parameters
    ----------
    client : deapi.Client
        Client object to interact with the DE API
    name : str
        Name of the property collection
    properties : list
        List of property names in the collection

    Notes
    -----
    This class is mostly used via the client."property_collection" attribute which groups
    properties together for easier access.  Groups are determined by properties which have
    names that start with the same string. For example, the properties "Group - Property 1"
    would allow access to the property using client.group["Property 1"]
    """
    def __init__(self, client, name, properties):
        self.properties = {}
        self.client = client
        self.name = name
        for prop in properties:
            new_str = prop.split(" - ")[1].lower().strip().replace(" ", "_")
            new_str2 = prop.split(" - ")[1].strip()
            self.properties[new_str] = prop
            self.properties[new_str2] = prop

    def __call__(self, *args, **kwargs):
        for key, value in kwargs.items():
            self.client.set_property(self.properties[key], value)

    def __getitem__(self, item):
        if item in self.properties:
            name = self.properties[item]
        else:
            raise KeyError(f"Property {item} not found")
        return self.client.get_property(name)

    def __setitem__(self, key, value):
        if isinstance(value, bool):
            if value:
                value = "On"
            else:
                value = "Off"
        if key in self.properties:
            name = self.properties[key]
        else:
            raise KeyError(f"Property {key} not found")
        self.client.set_property(name, value)

    def _repr_html_(self):
        table = """
        <table border="1">
            <tr>
                <th>Property</th>
                <th>Value</th>
            </tr>
        """
        for prop in self.properties:
            if prop.islower():
                table += f"""
                <tr>
                    <td>{prop}</td>
                    <td>{self[prop]}</td>
                </tr>
                """
        table += "</table>"
        return table

    def gui(self, properties=None):
        from ipywidgets import widgets, VBox, HBox, Button, Output
        from IPython.display import display

        # Create a dictionary to hold the widgets for each property
        self.widgets = {}

        # Create a VBox to hold all the property widgets
        form_items = []

        if properties is None:
            properties = self.properties

        for prop in properties:
            if prop.islower():
                # Determine the data type and create an appropriate widget
                # TODO: Add support for checking the property spec.
                current_value = self.client.get_property(self.properties[prop])
                if isinstance(current_value, bool):
                    widget = widgets.Checkbox(value=current_value, description=prop)
                elif isinstance(current_value, int):
                    widget = widgets.IntText(value=current_value, description=prop)
                elif isinstance(current_value, float):
                    widget = widgets.FloatText(value=current_value, description=prop)
                else:
                    widget = widgets.Text(value=current_value, description=prop)

                self.widgets[prop] = widget
                form_items.append(widget)

        # Create a button to submit the changes
        submit_button = Button(description="Submit")
        output = Output()

        def on_submit(b):
            with output:
                for prop, widget in self.widgets.items():
                    self.client.set_property(self.properties[prop], widget.value)
                for prop, widget in self.widgets.items():
                    widget.value = self.client.get_property(self.properties[prop])
                print("Properties updated.")

        submit_button.on_click(on_submit)

        return VBox(form_items + [submit_button, output])


class VirtualMask:
    """Class to interact with virtual masks in the DE API

    Parameters
    ----------
    client : deapi.Client
        Client object to interact with the DE API
    index : int
        Index of the virtual mask

    Notes
    -----
    This class is mostly used via the client.virtual_masks property which is a list
    of VirtualMask objects.
    """
    def __init__(self, client, index):
        self.client = client
        self.index = index

    def __getitem__(self, item):
        full_img = self.client.get_virtual_mask(self.index)
        return full_img[item]

    def __setitem__(self, key, value):
        string = f"Scan - Virtual Detector {self.index} Shape"
        if not self.client[string] == "Arbitrary":
            warn("Virtual mask shape is not set to Arbitrary. Setting to Arbitrary.")
            self.client[string] = "Arbitrary"
        full_img = self.client.get_virtual_mask(self.index)
        if value > 3 or value < 0:
            raise ValueError(
                "Value must be between 0 and 2. Please use 2 for positive mask,"
                " 0 for negative mask, and 0 for no mask."
            )
        full_img[key] = value
        self.client.set_virtual_mask(
            self.index, w=full_img.shape[0], h=full_img.shape[1], mask=full_img
        )

    def plot(self, ax=None, **kwargs):
        """Plot the virtual mask using matplotlib

        Parameters
        ----------
        ax : matplotlib.axes.Axes, optional
            Axes object to plot the virtual mask on. If not provided, a new figure will be created.
        **kwargs
            Additional keyword arguments to pass to ax.imshow

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> fig, ax = plt.subplots()
        >>> mask.plot(ax=ax)

        """
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots()
        ax.imshow(self.client.get_virtual_mask(self.index), vmax=3, vmin=0, **kwargs)
        return ax

    @property
    def calculation(self):
        """Calculation mode for the virtual mask
        """
        string = f"Scan - Virtual Detector {self.index} Calculation"
        return self.client[string]

    @calculation.setter
    def calculation(self, value):
        """Set the calculation mode for the virtual mask
        """
        string = f"Scan - Virtual Detector {self.index} Calculation"
        self.client[string] = value
