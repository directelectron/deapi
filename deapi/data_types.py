"""File containing the data types used in the DE API"""

#
# Last update: 2024-08-07
# cfrancis@directelectron.com


from enum import Enum
from enum import IntEnum
import warnings


class FrameType(Enum):
    """An Enum of the different frame types that can be returned by the DE API"""

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
    """An Enum describing the pixel format of the image data returned by the DE API"""

    UINT8 = 1  # 8-bit integer
    UINT16 = 5  # 16-bit integer
    FLOAT32 = 13  # 32-bit float
    AUTO = -1  # Automatically determined by the server


class DataType(Enum):
    """An Enum describing the data type of the image data returned by the DE API"""

    DEUndef = -1
    DE8u = 1
    DE16u = 5
    DE16s = 7
    DE32f = 13


class MovieBufferStatus(Enum):
    """An Enum describing the status of the movie buffer in the DE API"""

    UNKNOWN = 0
    FAILED = 1
    TIMEOUT = 3
    FINISHED = 4
    OK = 5


class ContrastStretchType(IntEnum):
    """An Enum describing the different types of contrast stretching that can be applied to an image"""

    NONE = 0
    MANUAL = 1
    LINEAR = 2
    DIFFRACTION = 3
    THONRINGS = 4
    NATURAL = 5
    HIGHCONTRAST = 6
    WIDERANGE = 7


class Attributes:
    """Class to hold attributes for getting the result of an image acquisition

    Parameters
    ----------
    center_x : float, optional
        Center x coordinate of the image
    center_y : float, optional
        Center y coordinate of the image
    zoom : float, optional
        Zoom level of the image
    window_width : int, optional
        Width of the window in pixels
    window_height : int, optional
        Height of the window in pixels
    fft : bool, optional
        Whether the image is in Fourier space
    linear_stretch : bool, optional
        Whether to apply linear stretching to the image
    stretch_type : int, optional
        Type of contrast stretching to apply
    manual_stretch_min : float, optional
        Minimum value for manual contrast stretching
    manual_stretch_max : float, optional
        Maximum value for manual contrast stretching
    manual_stretch_gamma : float, optional
        Gamma value for manual contrast stretching


    """

    def __init__(
        self,
        center_x: int = 0,
        center_y: int = 0,
        zoom: float = 1.0,
        window_width: int = 0,
        window_height: int = 0,
        fft: bool = False,
        linear_stretch: bool = False,
        stretch_type: int = ContrastStretchType.LINEAR,
        manual_stretch_min: float = 0.0,
        manual_stretch_max: float = 0.0,
        manual_stretch_gamma: float = 1.0,
        outlier_percentage: float = 2.0,
        buffered: bool = False,
        timeout_msec: float = -1,
        frame_width: int = 0,
        frame_height: int = 0,
        dataset_name: str = None,
        acq_index: int = 0,
        acq_finished: bool = False,
        image_index: int = 0,
        frame_count: int = 0,
        image_min: float = 0,
        image_max: float = 0,
        image_mean: float = 0,
        image_std: float = 0,
        eppix: float = 0,
        eps: float = 0,
        eppixps: float = 0,
        epa2: float = 0,
        eppixpf=0,
        eppix_incident=0,
        eps_incident=0,
        eppixps_incident=0,
        epa2_incident=0,
        eppixpf_incident=0,
        under_exposure_rate=0,
        over_exposure_rate=0,
        timestamp=0,
        auto_stretch_min=0.0,
        auto_stretch_max=0.0,
        auto_stretch_gamma=1.0,
        saturation=0.0,
    ):

        self.centerX = center_x
        self.centerY = center_y
        self.zoom = zoom
        self.windowWidth = window_width
        self.windowHeight = window_height
        self.fft = fft
        self.linearStretch = linear_stretch
        self.stretchType = stretch_type
        self.manualStretchMin = manual_stretch_min
        self.manualStretchMax = manual_stretch_max
        self.manualStretchGamma = manual_stretch_gamma
        self.outlierPercentage = outlier_percentage
        self.buffered = buffered
        self.timeoutMsec = timeout_msec
        self.frameWidth = frame_width
        self.frameHeight = frame_height
        self.datasetName = dataset_name
        self.acqIndex = acq_index
        self.acqFinished = acq_finished
        self.imageIndex = image_index
        self.frameCount = frame_count
        self.imageMin = image_min
        self.imageMax = image_max
        self.imageMean = image_mean
        self.imageStd = image_std
        self.eppix = eppix
        self.eps = eps
        self.eppixps = eppixps
        self.epa2 = epa2
        self.eppixpf = eppixpf
        self.eppix_incident = eppix_incident
        self.eps_incident = eps_incident
        self.eppixps_incident = eppixps_incident
        self.epa2_incident = epa2_incident
        self.eppixpf_incident = eppixpf_incident
        self.underExposureRate = under_exposure_rate
        self.overExposureRate = over_exposure_rate
        self.timestamp = timestamp
        self.autoStretchMin = auto_stretch_min
        self.autoStretchMax = auto_stretch_max
        self.autoStretchGamma = auto_stretch_gamma
        self.saturation = saturation


class Histogram:
    """Class to hold the histogram data from an image acquisition

    Parameters
    ----------
    min : float, optional
        minimum histogram value, if min and max is set to the same value, or in trial of gain acquisition mode,
        the server will determine this value.
    max : float, optional
        maximum histogram value, if min and max is set to the same value, or in trial of gain acquisition mode,
        the server will determine this value.
    upper_most_local_maxima : int, optional
        upper local max histogram value
    bins : int, optional
        number of bins requested, 0 means histogram data is not requested
    data : list, optional
        buffer containing histogram data
    """

    def __init__(
        self,
        min: float = 0.0,
        max: float = 0.0,
        upper_most_local_maxima: int = 0,
        bins: int = 256,
        data=None,
    ):
        self.min = min
        self.max = max
        self.upperMostLocalMaxima = upper_most_local_maxima
        self.bins = bins
        self.data = data


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

    def __init__(
        self,
        headerBytes: int = 0,
        imageBufferBytes: int = 0,
        frameIndexStartPos: int = 0,
        imageStartPos: int = 0,
        imageW: int = 0,
        imageH: int = 0,
        framesInBuffer: int = 0,
        imageDataType: int = DataType.DEUndef,
    ):

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
    """Class to hold the specification of a property in the DE API

    Parameters
    ----------
    data_type : str, optional
        Data type of the property
    value_type : str, optional
        Value type of the property
    category : str, optional
        Category of the property
    options : list, optional
        List of options for the property
    default_value : str, optional
        Default value of the property
    current_value : str, optional
        Current value of the property
    """

    def __init__(
        self,
        data_type: str = None,
        value_type: str = None,
        category: str = None,
        options: list = None,
        default_value=None,
        current_value=None,
    ):
        self.dataType = data_type
        self.valueType = value_type
        self.category = category
        self.options = options
        self.defaultValue = default_value
        self.currentValue = current_value

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
            warnings.warn(
                "Virtual mask shape is not set to Arbitrary. Setting to Arbitrary."
            )
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
        """Calculation mode for the virtual mask"""
        string = f"Scan - Virtual Detector {self.index} Calculation"
        return self.client[string]

    @calculation.setter
    def calculation(self, value):
        """Set the calculation mode for the virtual mask"""
        string = f"Scan - Virtual Detector {self.index} Calculation"
        self.client[string] = value
