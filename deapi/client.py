# File containing the Client for connecting to the DE-Server
#
# Last update: 2024-08-07
# cfrancis@directelectron.com


# Python System imports
import socket
import sys
import struct
import time
import os
import logging
import mmap
from datetime import datetime
from time import sleep
import re
from typing import List
from enum import Enum

import numpy as np

# External package imports
from PIL import Image
import numpy


# Internal package imports
from deapi.data_types import (
    FrameType,
    PixelFormat,
    Attributes,
    Histogram,
    PropertySpec,
    MovieBufferStatus,
    MovieBufferInfo,
    DataType,
    PropertyCollection,
    VirtualMask,
)


from deapi.buffer_protocols import pb
from deapi.version import version, commandVersion
from deapi.version import commandVersion as cVersion
import functools


## the commandInfo contains [VERSION_MAJOR.VERSION_MINOR.VERSION_PATCH.VERSION_REVISION]


logLevel = logging.INFO
logging.basicConfig(format="%(asctime)s DE %(levelname)-8s %(message)s", level=logLevel)
log = logging.getLogger("DECameraClientLib")
log.info("Python    : " + sys.version.split("(")[0])
log.info("DEClient  : " + version)
log.info("CommandVer: " + str(commandVersion))
log.info("logLevel  : " + str(logging.getLevelName(logLevel)))


def write_only(func):
    def wrapper(*args, **kwargs):
        if args[0].read_only:
            log.error("Client is read-only. Cannot set property.")
            return
        else:
            return func(*args, **kwargs)

    return wrapper


def disable_scan(func):
    def wrapper(*args, **kwargs):
        print("Disabling scan")
        initial_scan = args[0]["Scan - Enable"]
        args[0].set_property("Scan - Enable", False)
        ans = func(*args, **kwargs)
        args[0].set_property("Scan - Enable", initial_scan)
        return ans

    return wrapper


class Client:
    """A class for connecting to the DE-Server

    Examples
    --------
    >>> client = Client()
    >>> client.connect()
    >>> client["Exposure Time (seconds)"]
    """

    def __init__(self):
        pass

    def set_log_level(self, level):
        log = logging.getLogger("DECameraClientLib")
        log.setLevel(level)
        log.info("Log level set to %s", level)
        return

    def __str__(self):
        return f"Client(host={self.host}, port={self.port}, camera={self.get_current_camera()})"

    def _ipython_key_completions_(self):
        return self.list_properties()

    def _repr_html_(self):
        table = f"""
		<table>
			<tr>
				<th>Host</th>
				<th>Port</th>
				<th>Current Camera</th>
			</tr>
			<tr>
				<td>{self.host}</td>
				<td>{self.port}</td>
				<td>{self.currCamera}</td>
			</tr>
		</table>
        <details>
            <summary>Current Info</summary>
            <pre>
                {self.get_current_info()}
            </pre>
        </details>
        """
        return table

    def gui(self):
        from IPython.display import display

        display(self)

    def __setitem__(self, key, value):
        self.set_property(key, value)

    def __getitem__(self, key):
        return self.get_property(key)

    def get_current_info(self):
        prop_list = self.list_properties()
        values = self.get_properties(prop_list)
        text = ""
        for p, v in zip(prop_list, values):
            text += f"{p}: {v} \n"
        return text

    def _initialize_attributes(self):
        all_properties = self.list_properties()
        collections = [p.split(" - ")[0] for p in all_properties if " - " in p]
        unique_collections = np.unique(collections)
        for collection in unique_collections:
            stripped = collection.lower().strip().replace(" ", "_")
            props = [p for p in all_properties if collection + " -" in p]
            setattr(
                self,
                stripped,
                PropertyCollection(client=self, name=collection, properties=props),
            )

    def connect(self, host: str = "127.0.0.1", port: int = 13240, read_only=False):
        """Connect to DE-Server

        Parameters
        ----------
        host : str, optional
            The host to connect to, by default "127.0.0.1" for local connection
        port : int, optional
            The port to connect to, by default 13240
        """
        if host == "localhost" or host == "127.0.0.1":
            tcpNoDelay = 0  # on loopback interface, nodelay causes delay

            if self.usingMmf:
                self.mmf = mmap.mmap(0, MMF_DATA_BUFFER_SIZE, "ImageFileMappingObject")
                self.mmf[0] = True
        else:
            self.usingMmf = False  # Disabled MMF if connected remotely
            tcpNoDelay = 1

        if logLevel == logging.DEBUG:
            log.debug("Connecting to server: %s", host)

        self.socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM
        )  # Create a socket (SOCK_STREAM means a TCP socket)
        self.socket.connect(
            (host, port)
        )  # Connect to server reading port for sending data
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, tcpNoDelay)
        self.socket.setblocking(False)
        self.socket.settimeout(2)

        self.cameras = self.__getStrings(self.LIST_CAMERAS)
        if logLevel == logging.DEBUG:
            log.debug("Available cameras: %s", self.cameras)

        self.currCamera = self.cameras[0]
        if logLevel == logging.DEBUG:
            log.debug("Current camera: %s", self.currCamera)

        self.connected = True
        self.host = host
        self.port = port
        log.info("Connected to server: %s, port: %d", host, port)

        serverVersion = self.GetProperty("Server Software Version")
        serverVersion = re.findall(r"\d+", serverVersion)

        version = [int(part) for part in serverVersion[:4]]
        temp = version[2] + version[1] * 1000 + version[0] * 1000000

        if cVersion >= 12:
            self.set_client_read_only(read_only)

        if temp >= 2007004:
            ## version after 2.7.4
            commandVersion = 12
        elif temp >= 2007003:
            ## version after 2.7.3
            commandVersion = 11
        elif temp >= 2007002:
            ## version after 2.7.2
            commandVersion = 10
        elif temp >= 2005025:
            ##version after 2.5.25
            commandVersion = 4
        elif temp >= 2001017:
            ## version after 2.1.17
            commandVersion = 3
        self._initialize_attributes()
        self.update_scan_size()
        self.update_image_size()
        self.virtual_masks = []
        for i in range(4):
            self.virtual_masks.append(VirtualMask(client=self, index=i))

    def set_client_read_only(self, read_only):
        self.read_only = read_only
        command = self._addSingleCommand(self.SET_CLIENT_READ_ONLY, None, [read_only])
        response = self._sendCommand(command)
        return response

    def update_scan_size(self):
        self.scan_sizex = self["Scan - Size X"]
        self.scan_sizey = self["Scan - Size Y"]

    def update_image_size(self):
        self.image_sizex = self["Image Size X (pixels)"]
        self.image_sizey = self["Image Size Y (pixels)"]

    def disconnect(self):
        """
        Disconnects from the server.
        Closes the memory-mapped file (mmf) if it is open.
        Closes the socket connection if it is open.
        Sets the 'connected' flag to False.
        """
        if self.mmf != 0:
            self.mmf.close()

        if self.connected:
            self.socket.close()
            self.socket.close()
            self.connected = False
            log.info("Disconnected.")

    def list_cameras(self) -> List[str]:
        """
        List the available cameras on the server.
        """
        return self.cameras

    def get_virtual_mask(self, index):
        mask_name = f"virtual_mask{index}"
        a = Attributes()
        a.windowWidth = self["Image Size X (pixels)"]
        a.windowHeight = self["Image Size Y (pixels)"]
        (
            res,
            _,
            _,
            _,
        ) = self.get_result(mask_name, DataType.DE8u, attributes=a)
        return res

    def get_current_camera(self) -> str:
        """
        Get the current camera on the server.
        """
        if self.currCamera is None:
            return "No current camera"
        else:
            return self.currCamera

    @write_only
    def set_current_camera(self, camera_name: str = None):
        """
        Set the current camera on the server.
        """
        if camera_name is None:
            return False

        self.currCamera = camera_name

        if logLevel == logging.DEBUG:
            log.debug("current camera: %s", camera_name)

        self.refreshProperties = True
        return True

    def list_properties(self, options=None, search=None):
        """
        Get a list of property names from the current camera on DE-Server

        Parameters
        ----------
        options : list, optional
            Options to pass to the server, by default None
        """
        available_properties = self.__getStrings(self.LIST_PROPERTIES, options)
        if available_properties != False:
            self.available_properties = available_properties

        if logLevel == logging.DEBUG:
            log.debug("Available camera properties: %s", available_properties)
        if search is not None:
            available_properties = [p for p in available_properties if search in p]
        return available_properties

    def get_property_spec(self, propertyName: str):
        """
        Get a list of allowed values for a property of the current camera on DE-Server

        Parameters
        ----------
        propertyName : str
            The name of the property to get the allowed values for
        """
        t0 = self.GetTime()
        values = False
        command = self._addSingleCommand(self.LIST_ALLOWED_VALUES, propertyName)
        response = self._sendCommand(command)
        if response == False:
            return None

        values = self.__getParameters(response.acknowledge[0])

        propSpec = PropertySpec()
        propSpec.dataType = values[0]
        propSpec.valueType = values[1]
        propSpec.category = values[len(values) - 3]
        propSpec.options = list(values[2 : len(values) - 3])
        propSpec.defaultValue = str(values[len(values) - 2])
        propSpec.currentValue = str(values[len(values) - 1])

        optionsLength = len(propSpec.options)

        if propSpec.valueType == "Range":
            if optionsLength == 2:
                rangeString = ""
                for i in range(optionsLength):
                    if propSpec.dataType == "Integer":
                        rangeString += str(int(propSpec.options[i]))
                    else:
                        rangeString += str(propSpec.options[i])
                    if i == 0:
                        rangeString += str(" - ")

                propSpec.options.append(rangeString)

        if propSpec.valueType == "Set":
            for i in range(optionsLength):
                if propSpec.defaultValue == propSpec.options[i]:
                    if propSpec.defaultValue != "":
                        propSpec.options[i] = propSpec.defaultValue + str("*")
                    else:
                        emptyStringIndex = i
            if propSpec.defaultValue == "":
                propSpec.options.pop(emptyStringIndex)

        if "allow_all" in propSpec.valueType:
            propSpec.options = ""
        elif propSpec.dataType == "String":
            propSpec.options = str(list(map(lambda a: str(a), propSpec.options)))[1:-1]
        else:
            propSpec.options = str(propSpec.options)[1:-1]

        return propSpec

    def property_valid_values(self, propertyName: str):
        """
        Get a list of allowed values for a property of the current camera on DE-Server
        """
        t0 = self.GetTime()
        values = False
        command = self._addSingleCommand(self.LIST_ALLOWED_VALUES, propertyName)
        response = self._sendCommand(command)
        if response != False:
            values = self.__getParameters(response.acknowledge[0])

            if logLevel == logging.DEBUG:
                log.debug(
                    "get allowed property values: %s = %s, completed in %.1f ms",
                    propertyName,
                    values,
                    (self.GetTime() - t0) * 1000,
                )

        return values

    def get_property(self, propertyName: str):
        """
        Get the value of a property of the current camera on DE-Server

        Parameters
        ----------
        propertyName : str
            The name of the property to get the value of
        """
        t0 = self.GetTime()
        ret = False

        if propertyName is not None:
            command = self._addSingleCommand(self.GET_PROPERTY, propertyName)
            response = self._sendCommand(command)
            if response != False:
                values = self.__getParameters(response.acknowledge[0])
                if type(values) is list:
                    if len(values) > 0:
                        ret = values[0]  # always return the first value
                    else:
                        ret = values

                if logLevel == logging.DEBUG:
                    log.debug(
                        "GetProperty: %s = %s, completed in %.1f ms",
                        propertyName,
                        values,
                        (self.GetTime() - t0) * 1000,
                    )

        return ret

    def get_server_version(self):
        """
        Get the server software version
        """
        server_version = self.GetProperty("Server Software Version")
        server_version = re.findall(r"\d+", server_version)

        ver = [int(part) for part in server_version[:4]]
        res = ver[2] + ver[1] * 1000 + ver[0] * 1000000
        return res

    def get_properties(self, names=None):
        if names is None:
            names = self.list_properties()
        return [self.get_property(p) for p in names]

    @property
    def acquiring(self):
        """Check if the camera is currently acquiring images. (bool)"""
        return self.get_property("Acquisition Status") == "Acquiring"

    @write_only
    def set_property(self, name: str, value):
        """
        Set the value of a property of the current camera on DE-Server

        Parameters
        ----------
        name : str
            The name of the property to set the value of
        value : any
            The value to set the property to
        """
        t0 = self.GetTime()
        ret = False

        if name is not None and value is not None:
            command = self._addSingleCommand(self.SET_PROPERTY, name, [value])
            response = self._sendCommand(command)
            if response != False:
                ret = response.acknowledge[0].error != True
                self.refreshProperties = True

        if logLevel == logging.DEBUG:
            log.debug(
                "SetProperty: %s = %s, completed in %.1f ms",
                name,
                value,
                (self.GetTime() - t0) * 1000,
            )

        return ret

    @write_only
    def set_property_and_get_changed_properties(self, name, value, changedProperties):
        """
        Set the value of a property of the current camera on DE-Server and get all of
        the changed properties.  This is useful for testing and determining how certain
        properties affect others.

        Parameters
        ----------
        name : str
            The name of the property to set the value of
        value : any
            The value to set the property to
        changedProperties : list
            List of properties that have changed
        """
        t0 = self.GetTime()
        ret = False

        if name is not None and value is not None:
            command = self._addSingleCommand(
                self.SET_PROPERTY_AND_GET_CHANGED_PROPERTIES, name, [value]
            )
            response = self._sendCommand(command)
            if response != False:
                ret = response.acknowledge[0].error != True
                self.refreshProperties = True

            if ret:
                ret = self.ParseChangedProperties(changedProperties, response)
        if logLevel == logging.DEBUG:
            log.debug(
                "SetProperty: %s = %s, completed in %.1f ms",
                name,
                value,
                (self.GetTime() - t0) * 1000,
            )

        return ret

    @write_only
    def set_engineering_mode(self, enable, password):
        """
        Set the engineering mode of the current camera on DE-Server. Mostly for internal testing.

        Parameters
        ----------
        enable : bool
            Enable or disable engineering mode
        password : str
            The password to enable engineering mode
        """
        ret = False

        command = self._addSingleCommand(self.SET_ENG_MODE, None, [enable, password])
        response = self._sendCommand(command)
        if response != False:
            ret = response.acknowledge[0].error != True
            self.refreshProperties = True
        return ret

    @write_only
    def setEngModeAndGetChangedProperties(self, enable, password, changedProperties):

        ret = False

        command = self.__addSingleCommand(
            self.SET_ENG_MODE_GET_CHANGED_PROPERTIES, None, [enable, password]
        )
        response = self.__sendCommand(command)
        if response != False:
            ret = response.acknowledge[0].error != True
            self.refreshProperties = True

        if ret:
            ret = self.ParseChangedProperties(changedProperties, response)

        return ret

    @write_only
    def set_hw_roi(self, offsetX: int, offsetY: int, sizeX: int, sizeY: int):
        """
        Set the hardware region of interest (ROI) of the current camera on DE-Server.

        Parameters
        ----------
        offsetX : int
            The x offset of the ROI
        offsetY : int
            The y offset of the ROI
        sizeX : int
            The width of the ROI
        sizeY : int
            The height of the ROI
        """
        t0 = self.GetTime()
        ret = False

        command = self._addSingleCommand(
            self.SET_HW_ROI, None, [offsetX, offsetY, sizeX, sizeY]
        )
        response = self._sendCommand(command)
        if response != False:
            ret = response.acknowledge[0].error != True
            self.refreshProperties = True

        if logLevel == logging.DEBUG:
            log.debug(
                "SetHwRoi: (%i,%i,%i,%i) , completed in %.1f ms",
                offsetX,
                offsetY,
                sizeX,
                sizeY,
                (self.GetTime() - t0) * 1000,
            )

        return ret

    @write_only
    def SetScanSize(self, sizeX, sizeY):

        t0 = self.GetTime()
        ret = False

        command = self.__addSingleCommand(self.SET_SCAN_SIZE, None, [sizeX, sizeY])
        response = self.__sendCommand(command)
        if response != False:
            ret = response.acknowledge[0].error != True
            self.refreshProperties = True

        if logLevel == logging.DEBUG:
            log.debug(
                "SetScanSize: (%i,%i) , completed in %.1f ms",
                sizeX,
                sizeY,
                (self.GetTime() - t0) * 1000,
            )

        return ret

    @write_only
    def SetScanSizeAndGetChangedProperties(self, sizeX, sizeY, changedProperties):
        t0 = self.GetTime()
        ret = False

        command = self.__addSingleCommand(
            self.SET_SCAN_SIZE_AND_GET_CHANGED_PROPERTIES, None, [sizeX, sizeY]
        )
        response = self.__sendCommand(command)
        if response != False:
            ret = response.acknowledge[0].error != True
            self.refreshProperties = True

        if ret:
            ret = self.ParseChangedProperties(changedProperties, response)

        if logLevel == logging.DEBUG:
            log.debug(
                "SetScanSize: (%i,%i) , completed in %.1f ms",
                sizeX,
                sizeY,
                (self.GetTime() - t0) * 1000,
            )

        return ret

    @write_only
    def SetScanROI(self, enable, offsetX, offsetY, sizeX, sizeY):

        t0 = self.GetTime()
        ret = False

        command = self.__addSingleCommand(
            self.SET_SCAN_SIZE, None, [enable, offsetX, offsetY, sizeX, sizeY]
        )
        response = self.__sendCommand(command)
        if response != False:
            ret = response.acknowledge[0].error != True
            self.refreshProperties = True

        if logLevel == logging.DEBUG:
            log.debug(
                "SetScanROI: (%i,%i,%i,%i) , completed in %.1f ms",
                offsetX,
                offsetY,
                sizeX,
                sizeY,
                (self.GetTime() - t0) * 1000,
            )

        return ret

    @write_only
    def SetScanROI(self, enable, offsetX, offsetY, sizeX, sizeY, changedProperties):
        t0 = self.GetTime()
        ret = False

        command = self.__addSingleCommand(
            self.SET_SCAN_ROI__AND_GET_CHANGED_PROPERTIES,
            None,
            [enable, offsetX, offsetY, sizeX, sizeY],
        )
        response = self.__sendCommand(command)
        if response != False:
            ret = response.acknowledge[0].error != True
            self.refreshProperties = True

        if ret:
            ret = self.ParseChangedProperties(changedProperties, response)

        if logLevel == logging.DEBUG:
            log.debug(
                "SetScanROI: (%i,%i,%i,%i) , completed in %.1f ms",
                offsetX,
                offsetY,
                sizeX,
                sizeY,
                (self.GetTime() - t0) * 1000,
            )

        return ret

    @write_only
    def set_hw_roi_and_get_changed_properties(
        self, offsetX: int, offsetY: int, sizeX: int, sizeY: int, changedProperties
    ):
        """
        Set the hardware region of interest (ROI) of the current camera on DE-Server and get all of
        the changed properties.  This is useful for testing and determining how certain
        properties affect others.

        Parameters
        ----------
        offsetX : int
            The x offset of the ROI
        offsetY : int
            The y offset of the ROI
        sizeX : int
            The width of the ROI
        sizeY : int
            The height of the ROI
        changedProperties : list
            List of properties that have changed
        """
        t0 = self.GetTime()
        ret = False

        command = self._addSingleCommand(
            self.SET_HW_ROI_AND_GET_CHANGED_PROPERTIES,
            None,
            [offsetX, offsetY, sizeX, sizeY],
        )
        response = self._sendCommand(command)
        if response != False:
            ret = response.acknowledge[0].error != True
            self.refreshProperties = True

        if ret:
            ret = self.ParseChangedProperties(changedProperties, response)

        if logLevel == logging.DEBUG:
            log.debug(
                "SetHwRoi: (%i,%i,%i,%i) , completed in %.1f ms",
                offsetX,
                offsetY,
                sizeX,
                sizeY,
                (self.GetTime() - t0) * 1000,
            )

        return ret

    @write_only
    def set_sw_roi(self, offsetX: int, offsetY: int, sizeX: int, sizeY: int):
        """
        Set the software region of interest (ROI) of the current camera on DE-Server.

        Parameters
        ----------
        offsetX : int
            The x offset of the ROI
        offsetY : int
            The y offset of the ROI
        sizeX : int
            The width of the ROI
        sizeY : int
            The height of the ROI
        """
        t0 = self.GetTime()
        ret = False

        command = self._addSingleCommand(
            self.SET_SW_ROI, None, [offsetX, offsetY, sizeX, sizeY]
        )
        response = self._sendCommand(command)
        if response != False:
            ret = response.acknowledge[0].error != True
            self.refreshProperties = True

        if logLevel == logging.DEBUG:
            log.debug(
                "SetSwRoi: (%i,%i,%i,%i) , completed in %.1f ms",
                offsetX,
                offsetY,
                sizeX,
                sizeY,
                (self.GetTime() - t0) * 1000,
            )

        return ret

    @write_only
    def set_sw_roi_and_get_changed_properties(
        self, offsetX, offsetY, sizeX, sizeY, changedProperties
    ):
        """
        Set the software region of interest (ROI) of the current camera on DE-Server and get all of
        the changed properties.  This is useful for testing and determining how certain
        properties affect others.

        Parameters
        ----------
        offsetX : int
            The x offset of the ROI
        offsetY : int
            The y offset of the ROI
        sizeX : int
            The width of the ROI
        sizeY : int
            The height of the ROI
        changedProperties : list
            List of properties that have changed
        """
        t0 = self.GetTime()
        ret = False

        command = self._addSingleCommand(
            self.SET_SW_ROI_AND_GET_CHANGED_PROPERTIES,
            None,
            [offsetX, offsetY, sizeX, sizeY],
        )
        response = self._sendCommand(command)
        if response != False:
            ret = response.acknowledge[0].error != True
            self.refreshProperties = True

        if ret:
            ret = self.ParseChangedProperties(changedProperties, response)

        if logLevel == logging.DEBUG:
            log.debug(
                "SetSWRoi: (%i,%i,%i,%i) , completed in %.1f ms",
                offsetX,
                offsetY,
                sizeX,
                sizeY,
                (self.GetTime() - t0) * 1000,
            )

        return ret

    def current_movie_buffer(self):
        movieBufferInfo = self.GetMovieBufferInfo()
        if movieBufferInfo.imageDataType == DataType.DE8u:
            imageType = numpy.uint8
        elif movieBufferInfo.imageDataType == DataType.DE16u:
            imageType = numpy.uint16
        elif movieBufferInfo.imageDataType == DataType.DE32f:
            imageType = numpy.float32

            ## Allocate movie buffers
        totalBytes = movieBufferInfo.headerBytes + movieBufferInfo.imageBufferBytes
        buffer = bytearray(totalBytes)
        return movieBufferInfo, buffer, totalBytes, imageType

    @write_only
    def start_acquisition(
        self,
        numberOfAcquisitions: int = 1,
        requestMovieBuffer=False,
        update=True,
    ):
        """
        Start acquiring images. Make sure all of the properties are set to the desired values.

        Parameters
        ----------
        numberOfAcquisitions : int, optional
            The number of acquisitions to repeat, by default 1
        requestMovieBuffer : bool, optional
            Request a movie buffer, by default False.  If True, the movie buffer will be returned
            with all of the frames.

        """
        start_time = self.GetTime()
        step_time = self.GetTime()

        if update:
            self.update_scan_size()
            self.update_image_size()

        if self.refreshProperties:
            self.roi_x = self.GetProperty("Crop Size X")
            self.roi_y = self.GetProperty("Crop Size Y")
            self.binning_x = self.GetProperty("Binning X")
            self.binning_y = self.GetProperty("Binning Y")
            self.width = self.GetProperty("Image Size X (pixels)")
            self.height = self.GetProperty("Image Size Y (pixels)")
            self.exposureTime = self.GetProperty("Exposure Time (seconds)")
            self.refreshProperties = False

        if logLevel == logging.DEBUG:
            lapsed = (self.GetTime() - step_time) * 1000
            log.debug(" Prepare Time: %.1f ms", lapsed)
            step_time = self.GetTime()

        if self.width * self.height == 0:
            log.error("  Image size is 0! ")
        else:
            bytesize = 0
            command = self._addSingleCommand(
                self.START_ACQUISITION, None, [numberOfAcquisitions, requestMovieBuffer]
            )

            if logLevel == logging.DEBUG:
                lapsed = (self.GetTime() - step_time) * 1000
                log.debug("   Build Time: %.1f ms", lapsed)
                step_time = self.GetTime()

            response = self._sendCommand(command)
            if logLevel == logging.DEBUG:
                lapsed = (self.GetTime() - step_time) * 1000
                log.debug(" Command Time: %.1f ms", lapsed)
                step_time = self.GetTime()

            if response != False:
                ret = response.acknowledge[0].error != True
                self.refreshProperties = True

        if logLevel == logging.DEBUG:
            lapsed = (self.GetTime() - step_time) * 1000
            log.debug("  Typing Time: %.1f ms", lapsed)
            step_time = self.GetTime()

        if logLevel <= logging.DEBUG:
            lapsed = (self.GetTime() - start_time) * 1000
            log.debug(
                "  Start Time: %.1f ms, ROI:[%d, %d], Binning:[%d, %d], Image size:[%d, %d]",
                lapsed,
                self.roi_x,
                self.roi_y,
                self.binning_x,
                self.binning_y,
                self.width,
                self.height,
            )

    @write_only
    def stop_acquisition(self):
        """
        Stop acquiring images.

        This can be called in the same thread or another thread to stop the current acquisitions.
        This will cause `get_result` calls to return immediately.
        """
        start_time = self.GetTime()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
        sock.sendto(b"PyClientStopAcq", (self.host, self.port))
        respond = sock.recv(32)
        if logLevel == logging.INFO:
            log.info(f"{self.host} {self.port} {respond}")
        if logLevel <= logging.DEBUG:
            lapsed = (self.GetTime() - start_time) * 1000
            log.debug("    Stop Time: %.1f ms", lapsed)

        return b"Stopped" in respond

    def get_result(
        self,
        frameType="singleframe_integrated",
        pixelFormat="UINT16",
        attributes="auto",
        histogram=None,
    ):
        """
        Get the specified type of frames in the desired pixel format and associated information.

        Parameters
        ----------
        frameType: FrameType
            The type of frame to get. Use the FrameType enum or a string.
            Most common:
                - virtual_image0 (or 1, 2, 3, 4)
                - external_image1 (or 2, 3, 4)
                - sumtotal
                - singleframe_integrated
        pixelFormat: PixelFormat
            The pixel format to get. Use the PixelFormat enum or a string.
            One of the following:
                - DE8u
                - DE16u
                - DE32f
                - DE64f
        attributes: Attributes
            Defines the image to be returned, some members can be updated.
            Some members of this parameter are input only, some are input/output.
        histogram: Histogram
            Returns the histogram if desired.
            Some members of this parameter are input only, some are input/output.

        Note
        ----
        During acquisition, live frames will be returned; after acquisition, the last image will be returned.
        """
        if isinstance(frameType, str):
            frameType = getattr(FrameType, frameType.upper())
        if isinstance(pixelFormat, str):
            pixelFormat = getattr(PixelFormat, pixelFormat)

        if attributes == "auto":
            attributes = Attributes()
            scan_images = [17, 18, 19, 20, 21, 22, 23, 24, 25]
            if frameType.value in scan_images:
                attributes.windowWidth = self.scan_sizex
                attributes.windowHeight = self.scan_sizey
            else:
                attributes.windowWidth = self.image_sizex
                attributes.windowHeight = self.image_sizey

        log.debug("GetResult frameType:%s, pixelFormat:%s", frameType, pixelFormat)
        start_time = self.GetTime()
        step_time = self.GetTime()

        if attributes == None:
            attributes = Attributes()

        if histogram == None:
            histogram = Histogram()

        if attributes.windowWidth > 0:
            self.width = attributes.windowWidth

        if attributes.windowHeight > 0:
            self.height = attributes.windowHeight

        image = None
        imageDataType = numpy.uint16

        if logLevel == logging.DEBUG:
            lapsed = (self.GetTime() - step_time) * 1000
            log.debug(" Prepare Time: %.1f ms", lapsed)
            step_time = self.GetTime()

        if histogram != None:
            histoMin = histogram.min
            histoMax = histogram.max
            histoBins = histogram.bins
        else:
            histoMin = 0
            histoMax = 0
            histoBins = 0

        if self.width * self.height == 0:
            log.error("  Image size is 0! ")
        else:
            bytesize = 0
            command = self._addSingleCommand(
                self.GET_RESULT,
                None,
                [
                    frameType.value,
                    pixelFormat.value,
                    attributes.centerX,
                    attributes.centerY,
                    attributes.zoom,
                    attributes.windowWidth,
                    attributes.windowHeight,
                    attributes.fft,
                    attributes.stretchType,
                    attributes.manualStretchMin,
                    attributes.manualStretchMax,
                    attributes.manualStretchGamma,
                    attributes.outlierPercentage,
                    attributes.timeoutMsec,
                    histoMin,
                    histoMax,
                    histoBins,
                ],
            )

            if logLevel == logging.DEBUG:
                lapsed = (self.GetTime() - step_time) * 1000
                log.debug("   Build Time: %.1f ms", lapsed)
                step_time = self.GetTime()
            response = self._sendCommand(command)
            if logLevel == logging.DEBUG:
                lapsed = (self.GetTime() - step_time) * 1000
                log.debug(" Command Time: %.1f ms", lapsed)
                step_time = self.GetTime()

            if response != False:
                values = self.__getParameters(response.acknowledge[0])
                if (
                    type(values) is list and len(values) >= 20
                ):  # This should be majorly simplified
                    i = 0
                    pixelFormat = PixelFormat(values[i])
                    i += 1
                    attributes.frameWidth = values[i]
                    i += 1
                    attributes.frameHeight = values[i]
                    i += 1
                    attributes.datasetName = values[i]
                    i += 1
                    attributes.acqIndex = values[i]
                    i += 1
                    attributes.acqFinished = values[i]
                    i += 1
                    attributes.imageIndex = values[i]
                    i += 1
                    attributes.frameCount = values[i]
                    i += 1
                    attributes.imageMin = values[i]
                    i += 1
                    attributes.imageMax = values[i]
                    i += 1
                    attributes.imageMean = values[i]
                    i += 1
                    attributes.imageStd = values[i]
                    i += 1
                    attributes.eppix = values[i]
                    i += 1
                    attributes.eps = values[i]
                    i += 1
                    attributes.eppixps = values[i]
                    i += 1
                    attributes.epa2 = values[i]
                    i += 1
                    attributes.eppixpf = values[i]
                    i += 1
                    if commandVersion >= 12:
                        attributes.eppix_incident = values[i]
                        i += 1
                        attributes.eps_incident = values[i]
                        i += 1
                        attributes.eppixps_incident = values[i]
                        i += 1
                        attributes.epa2_incident = values[i]
                        i += 1
                        attributes.eppixpf_incident = values[i]
                        i += 1
                    if commandVersion >= 11:
                        attributes.saturation = values[i]
                        i += 1
                    if commandVersion < 10:
                        attributes.underExposureRate = values[i]
                        i += 1
                        attributes.overExposureRate = values[i]
                        i += 1
                    attributes.timestamp = float(values[i])
                    i += 1
                    if commandVersion >= 10:
                        attributes.autoStretchMin = values[i]
                        i += 1
                        attributes.autoStretchMax = values[i]
                        i += 1
                        attributes.autoStretchGamma = values[i]
                        i += 1

                    if (
                        histogram != None
                        and histoBins > 0
                        and len(values) >= i + histogram.bins
                    ):
                        histogram.data = [0] * histogram.bins
                        histogram.min = values[i]
                        i += 1
                        histogram.max = values[i]
                        i += 1
                        if commandVersion >= 11:
                            histogram.upperMostLocalMaxima = values[i]
                            i += 1
                        for j in range(histogram.bins):
                            log.debug("Hist %d: %d" % (j, values[i + j]))
                            histogram.data[j] = values[i + j]

                    if pixelFormat == PixelFormat.FLOAT32:
                        imageDataType = numpy.float32
                    elif pixelFormat == PixelFormat.UINT16:
                        imageDataType = numpy.uint16
                    else:
                        imageDataType = numpy.uint8

                    self.width = attributes.frameWidth
                    self.height = attributes.frameHeight

                recvbyteSizeString = self._recvFromSocket(
                    self.socket, 4
                )  # get the first 4 bytes
                if len(recvbyteSizeString) == 4:
                    recvbyteSize = struct.unpack(
                        "I", recvbyteSizeString
                    )  # interpret as size
                    received_string = self._recvFromSocket(
                        self.socket, recvbyteSize[0]
                    )  # get the rest
                    data_header = pb.DEPacket()
                    data_header.ParseFromString(received_string)
                    bytesize = data_header.data_header.bytesize

                if self.usingMmf:
                    image = numpy.frombuffer(
                        self.mmf,
                        offset=MMF_DATA_HEADER_SIZE,
                        dtype=imageDataType,
                        count=self.width * self.height,
                    )
                    image.shape = [self.height, self.width]
                    bytesize = self.width * self.height * 2
                elif bytesize > 0:
                    packet = self._recvFromSocket(self.socket, bytesize)
                    if len(packet) == bytesize:
                        image = numpy.frombuffer(packet, imageDataType)
                        bytesize = self.height * self.width * 2
                        image.shape = [self.height, self.width]
                    else:
                        log.error(
                            "The size of the image does not match the expected size from "
                            "The header. Expected: %d, Received: %d",
                            bytesize,
                            len(packet),
                        )

                if logLevel == logging.DEBUG:
                    elapsed = self.GetTime() - step_time
                    log.debug(
                        "Transfer time: %.1f ms, %d bytes, %d mbps",
                        elapsed * 1000,
                        bytesize,
                        bytesize * 8 / elapsed / 1024 / 1024,
                    )
                    step_time = self.GetTime()

            if bytesize <= 0:
                log.error("  GetResut failed! An empty image will be returned.")
                image = None

            if logLevel == logging.DEBUG:
                lapsed = (self.GetTime() - step_time) * 1000
                log.debug("  Saving Time: %.1f ms", lapsed)
                step_time = self.GetTime()

        if image is None:
            log.error("  GetResut failed!")
        else:
            image = image.astype(imageDataType)

            if logLevel == logging.DEBUG:
                lapsed = (self.GetTime() - step_time) * 1000
                log.debug("  Typing Time: %.1f ms", lapsed)
                step_time = self.GetTime()

        if logLevel <= logging.DEBUG:
            lapsed = (self.GetTime() - start_time) * 1000
            log.debug(
                "GetResult frameType:%s, pixelFormat:%s ROI:[%d, %d] Binning:[%d, %d], Return size:[%d, %d], datasetName:%s acqCount:%d, frameCount:%d min:%.1f max:%.1f mean:%.1f std:%.1f %.1f ms",
                frameType,
                pixelFormat,
                attributes.datasetName,
                attributes.acqIndex,
                attributes.frameCount,
                attributes.imageMin,
                attributes.imageMax,
                attributes.imageMean,
                attributes.imageStd,
                lapsed,
            )

        return image, pixelFormat, attributes, histogram

    @write_only
    def set_virtual_mask(self, id, w, h, mask):
        """
        Set the virtual mask of the current camera on DE-Server.

        Parameters
        ----------
        id : int
            The id of the mask. 0-3
        w : int
            The width of the mask
        h : int
            The height of the mask
        mask : np.ndarray
            The mask to set
        """
        if id < 1 or id > 4:
            log.error(
                " SetVirtualMask The virtual mask id must be selected between 1-4"
            )
            ret = False
        elif w < 0 or h < 0:
            log.error(
                " SetVirtualMask The virtual mask width and height must greater than 0"
            )
            ret = False
        else:
            command = self._addSingleCommand(self.SET_VIRTUAL_MASK, None, [id, w, h])
            ret = True
            try:
                packet = (
                    struct.pack("I", command.ByteSize()) + command.SerializeToString()
                )
                self.socket.send(packet)
            except socket.error as e:
                ret = False

            if ret:
                mask_bytes = mask.tobytes()
                self.__sendToSocket(self.socket, mask_bytes, len(mask_bytes))

            ret = self.__ReceiveResponseForCommand(command) != False

        return ret

    def get_movie_buffer_info(self, movieBufferInfo=None, timeoutMsec=5000):
        """
        Get the movie buffer information of the current camera on DE-Server.

        Parameters
        ----------
        movieBufferInfo : MovieBufferInfo, optional
            The movie buffer information to get, by default None. If None
            a new MovieBufferInfo object will be created.
        timeoutMsec : int, optional
            The timeout in milliseconds, by default 5000"""

        if movieBufferInfo == None:
            movieBufferInfo = MovieBufferInfo()
        command = self._addSingleCommand(self.GET_MOVIE_BUFFER_INFO, None, None)

        response = self._sendCommand(command)

        if response != False:
            values = self.__getParameters(response.acknowledge[0])
            if type(values) is list:
                movieBufferInfo.headerBytes = values[0]
                movieBufferInfo.imageBufferBytes = values[1]
                movieBufferInfo.frameIndexStartPos = values[2]
                movieBufferInfo.imageStartPos = values[3]
                movieBufferInfo.imageW = values[4]
                movieBufferInfo.imageH = values[5]
                movieBufferInfo.framesInBuffer = values[6]
                dataType = values[7]
                movieBufferInfo.imageDataType = DataType(dataType)

        return movieBufferInfo

    def get_movie_buffer(
        self, movieBuffer, movieBufferSize, numFrames, timeoutMsec=5000
    ):
        """
        Get the movie buffer of the current camera on DE-Server. The movie buffer
        is a series of frames that are stored in memory and can be retrieved as
        a single buffer for faster processing.

        """

        movieBufferStatus = MovieBufferStatus.UNKNOWN
        retval = True

        command = self._addSingleCommand(self.GET_MOVIE_BUFFER, None, [timeoutMsec])
        response = self._sendCommand(command)

        if response != False:
            totalBytes = 0
            status = 0
            values = self.__getParameters(response.acknowledge[0])
            if type(values) is list:
                status = values[0]
                totalBytes = values[1]
                numFrames = values[2]
                movieBufferStatus = MovieBufferStatus(status)
                if movieBufferStatus == MovieBufferStatus.OK:
                    if totalBytes == 0 or movieBufferSize < totalBytes:
                        retval = False
                        log.error(
                            f"Image received did not have the expected size."
                            f"expected: {totalBytes}, received: {movieBufferSize}"
                        )
                    else:
                        print("reading movie buffer", totalBytes)
                        movieBuffer = self._recvFromSocket(self.socket, totalBytes)
                        print("Done reading movie buffer")
        else:
            retval = False

        if not retval:
            movieBufferStatus = MovieBufferStatus.FAILED

        return movieBufferStatus, totalBytes, numFrames, movieBuffer

    def save_image(self, image, fileName, textSize=0):
        t0 = self.GetTime()
        filePath = self.debugImagesFolder + fileName + ".tif"
        try:
            if not os.path.exists(self.debugImagesFolder):
                os.makedirs(self.debugImagesFolder)

            tiff = Image.fromarray(image)
            tiff.save(filePath)
            log.info("Saved %s" % filePath)

            # if textSize > 0:
            #     self.__saveText(image, fileName, textSize)

        except OSError:
            log.error("Failed to save file")

        if logLevel == logging.DEBUG or True:
            log.debug("Save time: %.1f ms", (self.GetTime() - t0) * 1000)

        return filePath

    def print_server_info(self, camera=None):
        """
        Print out the server information
        """
        if camera is None:
            camera = self["Camera Name"]
        print("Time        : " + datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
        print("Computer    : " + socket.gethostname())
        print("DE-Server   : " + self.GetProperty("Server Software Version"))
        print("CPU         : " + self.GetProperty("Computer CPU Info"))
        print("GPU         : " + self.GetProperty("Computer GPU Info"))
        print("Memory      : " + self.GetProperty("Computer Memory Info"))
        print("Camera Name : " + camera)
        print("Camera S/N  : " + str(self.GetProperty("Camera SN")))
        print("Sensor S/N  : " + str(self.GetProperty("Sensor Module SN")))
        print("Firmware    : " + str(self.GetProperty("Firmware Version")))
        print("Python      : " + sys.version.split("(")[0])
        print("Client      : " + version)
        print("Interrupt   : " + str(self.GetProperty("Interrupt Status")))

    def print_acquisition_info(self):
        """
        Print out the acquisition information
        """
        hwW = self.GetProperty("Hardware ROI - Size X")
        hwH = self.GetProperty("Hardware ROI - Size Y")
        hwX = self.GetProperty("Hardware ROI Offset X")
        hwY = self.GetProperty("Hardware ROI Offset Y")
        hwBinX = self.GetProperty("Hardware Binning X")
        hwBinY = self.GetProperty("Hardware Binning Y")

        swW = self.GetProperty("ROI Size X")
        swH = self.GetProperty("ROI Size Y")
        swX = self.GetProperty("ROI Offset X")
        swY = self.GetProperty("ROI Offset Y")
        swBinX = self.GetProperty("Binning X")
        swBinY = self.GetProperty("Binning Y")

        print("Test Pattern: " + self.GetProperty("Test Pattern"))
        print("Log Level   : " + self.GetProperty("Log Level"))
        print(
            "Sensor size : "
            + str(self.GetProperty("Sensor Size X (pixels)"))
            + " x "
            + str(self.GetProperty("Sensor Size Y (pixels)"))
        )
        print("HW ROI      : " + str("%d x %d at (%d, %d)" % (hwW, hwH, hwX, hwY)))
        print("HW Binning  : " + "%d x %d" % (hwBinX, hwBinY))
        print("SW ROI      : " + str("%d x %d at (%d, %d)" % (swW, swH, swX, swY)))
        print("SW Binning  : " + "%d x %d" % (swBinX, swBinY))
        print(
            "Image size  : "
            + str(self.GetProperty("Image Size X (pixels)"))
            + " x "
            + str(self.GetProperty("Image Size Y (pixels)"))
        )
        print("Max FPS     : " + str(self.GetProperty("Frames Per Second (Max)")))
        print("FPS         : " + str(self.GetProperty("Frames Per Second")))
        print("Grab Buffers: " + str(self.GetProperty("Grab Buffer Size")))

    def print_saving_info(self):
        """
        Print out the saving information
        """
        sys.stdout.write("Saving      : ")

        if self.GetProperty("Autosave Crude Frames") == "On":
            sys.stdout.write("crude ")
        if self.GetProperty("Autosave Raw Frames") == "On":
            sys.stdout.write("raw ")
        if self.GetProperty("Autosave Single Frames") == "On":
            sys.stdout.write("frames ")
        if self.GetProperty("Autosave Integrating Frames") == "On":
            sys.stdout.write("integrating frames ")
        if self.GetProperty("Autosave Movie") == "On":
            sys.stdout.write("movie(")
            sys.stdout.write(str(self.GetProperty("Autosave Movie - Sum Count")))
            sys.stdout.write(") ")
        if self.GetProperty("Autosave Final Image") == "On":
            sys.stdout.write("final ")

        print("")

    def grab(self, frames=1, dataSetName="", fileName=None):
        """
        Grab specified number of frames and print out stats. Mostly used for testing purposes

        Parameters
        ----------
        frames : int, optional
            The number of frames requested, by default 1
        dataSetName : str, optional
            Data set name to be used, by default ""
        fileName : str, optional
            Save the returned image as a file if provided, by default None
        """
        imageW = self.GetProperty("Image Size X (pixels)")
        imageH = self.GetProperty("Image Size Y (pixels)")
        fps = self.GetProperty("Frames Per Second")

        self.SetProperty("Exposure Time (seconds)", frames / fps)
        expoSec = self.GetProperty("Exposure Time (seconds)")
        maxExpoSec = self.GetProperty("Exposure Time Max (seconds)")
        prevSuffix = self.GetProperty("Autosave Filename Suffix")

        frames = round(expoSec * fps)
        # frames = expoSec * fps

        if dataSetName != "" and dataSetName != None:
            self.SetProperty("Autosave Filename Suffix", dataSetName)
            dataSetName = dataSetName + " "

        if dataSetName != None:
            sys.stdout.write("%s%dx%d fps:%.3f " % (dataSetName, imageW, imageH, fps))
            sys.stdout.flush()

        t0 = self.GetTime()
        self.StartAcquisition(1)

        frameType = FrameType.SUMTOTAL

        pixelFormat = PixelFormat.AUTO
        attributes = Attributes()
        histogram = Histogram()
        image = self.GetResult(frameType, pixelFormat, attributes, histogram)[0]

        duration = self.GetTime() - t0
        measuredFps = self.GetProperty("Measured Frame Rate")
        missedFrames = self.GetProperty("Missed Frames")

        frameCount = self.GetProperty("Number of Frames Processed")
        sys.stdout.write(
            "mfps:%.3f et:%.2fs dur:%.2fs frames:%d/%d %s %s, min:%4.1f max:%4.0f mean:%8.3f std:%8.3f timestamp:%10.6f"
            % (
                measuredFps,
                expoSec,
                duration,
                frameCount,
                frames,
                frameType,
                pixelFormat,
                attributes.imageMin,
                attributes.imageMax,
                attributes.imageMean,
                attributes.imageStd,
                attributes.timestamp,
            )
        )
        sys.stdout.flush()

        if max == 0:
            sys.stdout.write(", empty")

        if missedFrames > 0:
            sys.stdout.write(", missed:%d " % (missedFrames))

        sys.stdout.flush()

        self.WaitForSavingFiles(dataSetName == None)
        self.SetProperty("Autosave Filename Suffix", prevSuffix)

        if fileName and len(fileName) > 0:
            self.SaveImage(image, fileName)

        return image

    def wait_for_saving_files(self, quiet=True):
        """
        Wait for the saving files to complete
        """

        t0 = self.GetTime()
        saveCrude = True if self.GetProperty("Autosave Crude Frames") == "On" else False
        saveRaw = True if self.GetProperty("Autosave Raw Frames") == "On" else False
        saveFrame = (
            True if self.GetProperty("Autosave Single Frames") == "On" else False
        )
        saveMovie = True if self.GetProperty("Autosave Movie") == "On" else False
        counting = (
            True
            if self.GetProperty("Image Processing - Mode") != "Integrating"
            else False
        )

        saveIntegratingFrames = saveFrame and (
            not counting or self.GetProperty("Autosave Integrating Frames") == "On"
        )
        saveCountingFrames = saveFrame and counting
        saveIntegratingMovie = saveMovie and not counting
        saveCountingMovie = saveMovie and counting

        saveFinal = True if self.GetProperty("Autosave Final Image") == "On" else False
        expMode = self.GetProperty("Exposure Mode")

        if expMode == "Dark" or expMode == "Gain":
            repeats = self.GetProperty("Remaining Number of Acquisitions")
            remaining = self.GetProperty("Remaining Number of Acquisitions")
            if remaining > 0:
                for i in range(repeats * 10):
                    remaining = self.GetProperty("Remaining Number of Acquisitions")
                    if remaining > 0:
                        sleep(1)
                    else:
                        break
        elif (
            saveCrude
            or saveRaw
            or saveIntegratingFrames
            or saveCountingFrames
            or saveIntegratingMovie
            or saveCountingMovie
            or saveFinal
        ):
            for i in range(1000):
                if self.GetProperty("Autosave Status") in ["Starting", "In Progress"]:
                    if not quiet:
                        sys.stdout.write(".")
                        sys.stdout.flush()
                    sleep(1)
                else:
                    if not quiet:
                        sys.stdout.write(
                            " \tgrab:%4.0fMB/s"
                            % self.GetProperty("Speed - Grabbing (MB/s)")
                        )
                        sys.stdout.write(
                            " proc:%4.0fMB/s"
                            % self.GetProperty("Speed - Processing (MB/s)")
                        )
                        sys.stdout.write(
                            " save:%4.0fMB/s"
                            % self.GetProperty("Speed - Writing (MB/s)")
                        )

                        if saveCrude:
                            sys.stdout.write(
                                " crude:%d"
                                % self.GetProperty("Autosave Crude Frames Written")
                            )
                        if saveRaw:
                            sys.stdout.write(
                                " raw:%d"
                                % self.GetProperty("Autosave Raw Frames Written")
                            )
                        if saveIntegratingFrames:
                            # sys.stdout.write(" frames:%d" %  self.GetProperty("Autosave Single Frames - Frames Written") )
                            sys.stdout.write(
                                " integrating frames:%d"
                                % self.GetProperty(
                                    "Autosave Integrated Single Frames Written"
                                )
                            )
                        if saveCountingFrames:
                            sys.stdout.write(
                                " counting frames:%d"
                                % self.GetProperty(
                                    "Autosave Counted Single Frames Written"
                                )
                            )
                        if saveIntegratingMovie:
                            sys.stdout.write(
                                " integrating movie:%d"
                                % self.GetProperty(
                                    "Autosave Integrated Movie Frames Written"
                                )
                            )
                        if saveCountingMovie:
                            sys.stdout.write(
                                " counting movie:%d"
                                % self.GetProperty(
                                    "Autosave Counted Movie Frames Written"
                                )
                            )
                        if saveFinal:
                            sys.stdout.write(
                                " final sum count:%d"
                                % self.GetProperty("Autosave Final Image - Sum Count")
                            )

                    break

        duration = self.GetTime() - t0
        if not quiet:
            print(" %.1fs" % duration)
            sys.stdout.flush()

    # Start acquisition and get a single image
    # fileName: the image will be saved to disk if a file name is provided
    # textSize: a text file with pixel values will be saved if textSize is given, for debugging/test
    def get_image(self, pixelFormat=PixelFormat.AUTO, fileName=None, textSize=0):
        """
        Get a single image and save it to disk if a file name is provided

        Parameters
        ----------
        pixelFormat : PixelFormat, optional
            The pixel format of the image, by default PixelFormat.AUTO
        fileName : str, optional
            The file name to save the image, by default None
        textSize : int, optional
            The text size, by default 0
        """
        self.StartAcquisition(1)
        frameType = FrameType.SUMTOTAL

        if pixelFormat == "float32":
            pixelFormat = PixelFormat.FLOAT32

        elif pixelFormat == "uint16":
            pixelFormat = PixelFormat.UINT16

        attributes = Attributes()
        histogram = Histogram()
        image = self.GetResult(frameType, pixelFormat, attributes, histogram)[0]

        if fileName and len(fileName) > 0:
            self.SaveImage(image, fileName, textSize)

        return image

    @disable_scan
    def take_dark_reference(self, frameRate: float = 20):
        """
        Take dark reference images

        Parameters
        ----------
        frameRate : float, optional
            The frame rate, by default 20 frames per second
        """
        sys.stdout.write("Taking dark references: ")
        sys.stdout.flush()

        prevExposureMode = self.GetProperty("Exposure Mode")
        prevExposureTime = self.GetProperty("Exposure Time (seconds)")

        acquisitions = 20
        self.SetProperty("Exposure Mode", "Dark")
        self.SetProperty("Frames Per Second", frameRate)
        self.SetProperty("Exposure Time (seconds)", 1)
        self.StartAcquisition(acquisitions)

        while True:
            attributes = Attributes()
            histogram = Histogram()
            image = self.GetResult(
                FrameType.SUMTOTAL, PixelFormat.FLOAT32, attributes, histogram
            )

            sys.stdout.write(str(attributes.acqIndex) + " ")
            sys.stdout.flush()
            remaining = self.GetProperty("Remaining Number of Acquisitions")

            if remaining == 0:
                print("done.")
                break

        self.SetProperty("Exposure Mode", prevExposureMode)
        self.SetProperty("Exposure Time (seconds)", prevExposureTime)

    def get_time(self):
        """
        Get the current time from the system clock
        """
        if sys.version_info[0] < 3:
            return time.clock()
        else:
            return time.perf_counter()

    # private methods

    def __del__(self):
        if self.connected:
            self.disconnect()

    # get multiple parameters from a single acknowledge packet
    def __getParameters(self, single_acknowledge=None):
        output = []
        if single_acknowledge is None:
            return output
        if single_acknowledge.error == True:
            return output
        for one_parameter in single_acknowledge.parameter:
            if one_parameter.type == pb.AnyParameter.P_BOOL:
                output.append(one_parameter.p_bool)
            elif one_parameter.type == pb.AnyParameter.P_STRING:
                output.append(one_parameter.p_string)
            elif one_parameter.type == pb.AnyParameter.P_INT:
                output.append(one_parameter.p_int)
            elif one_parameter.type == pb.AnyParameter.P_FLOAT:
                output.append(one_parameter.p_float)
        return output

    # get strings from a single command response
    def __getStrings(self, command_id=None, param=None):
        if command_id is None:
            return False
        command = self._addSingleCommand(command_id, param)
        response = self._sendCommand(command)
        if response != False:
            return self.__getParameters(response.acknowledge[0])
        else:
            return False

    # add a new command (with optional label and parameter)
    def _addSingleCommand(self, command_id=None, label=None, params=None):
        if command_id is None:
            return False
        command = pb.DEPacket()  # create the command packet
        command.type = pb.DEPacket.P_COMMAND
        singlecommand1 = command.command.add()  # add the first single command
        singlecommand1.command_id = command_id + commandVersion * 100
        if not label is None:
            str_param = command.command[0].parameter.add()
            str_param.type = pb.AnyParameter.P_STRING
            str_param.p_string = label
            str_param.name = "label"

        if not params is None:
            for param in params:
                if isinstance(param, bool):
                    bool_param = command.command[0].parameter.add()
                    bool_param.type = pb.AnyParameter.P_BOOL
                    bool_param.p_bool = bool(param)
                    bool_param.name = "val"
                elif isinstance(param, int) or isinstance(param, np.int32):
                    int_param = command.command[0].parameter.add()
                    int_param.type = pb.AnyParameter.P_INT
                    int_param.p_int = int(param)
                    int_param.name = "val"
                elif isinstance(param, float):
                    float_param = command.command[0].parameter.add()
                    float_param.type = pb.AnyParameter.P_FLOAT
                    float_param.p_float = param
                    float_param.name = "val"
                else:
                    str_param = command.command[0].parameter.add()
                    str_param.type = pb.AnyParameter.P_STRING
                    str_param.p_string = str(param)
                    str_param.name = "val"
        return command

    # send single command and get a response, if error occurred, return False
    def _sendCommand(self, command=None):
        step_time = self.GetTime()

        if command is None:
            return False

        if len(command.camera_name) == 0:
            command.camera_name = (
                self.currCamera
            )  # append the current camera name if necessary

        try:
            packet = struct.pack("I", command.ByteSize()) + command.SerializeToString()
            res = self.socket.send(packet)
            # packet.PrintDebugString()
            # log.debug("sent result = %d\n", res)
        except:
            log.error("Error sending %s\n", command)

        if logLevel == logging.DEBUG:
            lapsed = (self.GetTime() - step_time) * 1000
            log.debug(" Send Time: %.1f ms", lapsed)
            step_time = self.GetTime()

        return self.__ReceiveResponseForCommand(command)

    def __ReceiveResponseForCommand(self, command):
        step_time = self.GetTime()

        recvbyteSizeString = self._recvFromSocket(
            self.socket, 4
        )  # get the first 4 byte

        if len(recvbyteSizeString) == 4:
            recvbyteSize = struct.unpack("I", recvbyteSizeString)  # interpret as size
            log.debug("-- recvbyteSize: " + str(recvbyteSize))
            received_string = self._recvFromSocket(
                self.socket, recvbyteSize[0]
            )  # get the rest
            if logLevel == logging.DEBUG:
                lapsed = (self.GetTime() - step_time) * 1000
                log.debug(" Recv Time: %.1f ms, %d bytes", lapsed, recvbyteSize[0])
                step_time = self.GetTime()

            Acknowledge_return = pb.DEPacket()
            Acknowledge_return.ParseFromString(received_string)  # parse the byte string
            if logLevel == logging.DEBUG:
                lapsed = (self.GetTime() - step_time) * 1000
                log.debug("Parse Time: %.1f ms", lapsed)
                step_time = self.GetTime()

            if (
                Acknowledge_return.type == pb.DEPacket.P_ACKNOWLEDGE
            ):  # has to be an acknowledge packet
                if len(command.command) <= len(Acknowledge_return.acknowledge):
                    error = False
                    for one_ack in Acknowledge_return.acknowledge:
                        error = error or one_ack.error
                    if error:
                        message = Acknowledge_return.acknowledge[0].error_message
                        if logLevel == logging.DEBUG:
                            log.error(
                                "Server returned error for request :\n"
                                + str(command)
                                + "\n"
                                + "Response :\n"
                                + str(message)
                            )
                        elif not message.startswith("Unknown property"):
                            log.error(message)
                    else:
                        if logLevel == logging.DEBUG:
                            lapsed = (self.GetTime() - step_time) * 1000
                            log.debug("  Ack Time: %.1f ms", lapsed)
                            step_time = self.GetTime()
                        return Acknowledge_return
                else:
                    log.error(
                        "len(command.command):%d != len(Acknowledge_return.acknowledge):%d",
                        len(command.command),
                        len(Acknowledge_return.acknowledge),
                    )
            else:
                log.error("Response from server is not ACK")
        else:
            log.error(
                "Server response is %d bytes, shorter than mimumum of 4 bytes",
                len(recvbyteSizeString),
            )

        return False

    def _recvFromSocket(self, sock, bytes):
        timeout = self.exposureTime * 10 + 30
        startTime = self.GetTime()
        self.socket.settimeout(timeout)

        buffer = b""

        total_len = len(buffer)
        upper_lim = 4096 * 4096 * 12  # 4096 #1024*256
        while total_len < bytes:
            bytes_left = bytes - total_len
            if bytes_left < upper_lim:
                packet_size = bytes_left
            else:
                packet_size = upper_lim
            loopTime = self.GetTime()
            try:
                buffer += sock.recv(packet_size)

            except socket.timeout:
                log.debug(
                    " __recvFromSocket : timeout in trying to receive %d bytes in %.1f ms",
                    bytes,
                    (self.GetTime() - loopTime) * 1000,
                )
                if self.GetTime() - startTime > timeout:
                    log.error(" __recvFromSocket: max timeout %d seconds", timeout)
                    break
                else:
                    pass  # continue further
            except:
                log.error(
                    "Unknown exception occurred. Current Length: %d in %.1f ms",
                    len(buffer),
                    (self.GetTime() - loopTime) * 1000,
                )
                break
            total_len = len(buffer)

        totalTimeMs = (self.GetTime() - startTime) * 1000
        Gbps = total_len * 8 / (totalTimeMs / 1000) / 1024 / 1024 / 1024
        log.debug(
            " __recvFromSocket :received %d of %d bytes in total in %.1f ms, %.1f Gbps",
            total_len,
            bytes,
            totalTimeMs,
            Gbps,
        )

        return buffer

    def __sendToSocket(self, sock, buffer, bytes):
        timeout = self.exposureTime * 10 + 30
        startTime = self.GetTime()
        self.socket.settimeout(timeout)

        retval = True
        chunkSize = 4096
        for i in range(0, len(buffer), chunkSize):
            try:
                sock.send(buffer[i : min(len(buffer), i + chunkSize)])
            except socket.timeout:

                log.debug(
                    " __sendToSocket : timeout in trying to send %d bytes in %.1f ms",
                    bytes,
                    (self.GetTime() - loopTime) * 1000,
                )
                if self.GetTime() - startTime > timeout:
                    log.error(" __recvFromSocket: max timeout %d seconds", timeout)
                    retval = False
                    break
                else:
                    pass  # continue further
            except socket.error as e:
                log.error(f"Error during send: {e}")
                # Handle the error as needed, e.g., close the connection
                retval = False
                break
        return buffer

    def __saveText(self, image, fileName, textSize):
        text = open(self.debugImagesFolder + fileName + ".txt", "w+")
        line = "%s: [%d x %d]\n" % (fileName, image.shape[1], image.shape[0])
        text.write(line)
        for i in range(min(image.shape[0], textSize)):
            for j in range(min(image.shape[1], textSize)):
                text.write("%8.3f\t" % image[i][j])

            if image.shape[1] > textSize:
                text.write(" ...\n")
            else:
                text.write("\n")

        if image.shape[0] > textSize:
            text.write("...\n")
        else:
            text.write("\n")

    def ParseChangedProperties(self, changedProperties, response):
        value = self.__getParameters(response.acknowledge[0])[0]

        props = value.split("|")

        try:
            for prop in props:
                p = prop.split(":")

                if len(p) == 2:
                    changedProperties[p[0]] = p[1]
        except Exception as e:
            log.error("Parse changed properties failed." + e.Message)

        return changedProperties

    # renamed methods to follow python standards
    GetServerVersion = get_server_version
    Connect = connect
    Disconnect = disconnect
    ListCameras = list_cameras
    GetCurrentCamera = get_current_camera
    SetCurrentCamera = set_current_camera
    ListProperties = list_properties
    GetPropertySpec = get_property_spec
    PropertyValidValues = property_valid_values
    GetProperty = get_property
    SetProperty = set_property
    SetPropertyAndGetChangedProperties = set_property_and_get_changed_properties
    setEngMode = set_engineering_mode
    SetHWROI = set_hw_roi
    SetHWROIAndGetChangedProperties = set_hw_roi_and_get_changed_properties
    SetSWROI = set_sw_roi
    SetSWROIAndGetChangedProperties = set_sw_roi_and_get_changed_properties
    StartAcquisition = start_acquisition
    StopAcquisition = stop_acquisition
    GetResult = get_result
    SetVirtualMask = set_virtual_mask
    GetMovieBufferInfo = get_movie_buffer_info
    GetMovieBuffer = get_movie_buffer
    SaveImage = save_image
    PrintServerInfo = print_server_info
    PrintAcqInfo = print_acquisition_info
    PrintSavingInfo = print_saving_info
    Grab = grab
    WaitForSavingFiles = wait_for_saving_files
    GetImage = get_image
    TakeDarkReference = take_dark_reference
    GetTime = get_time

    # method setProperty was renamed to SetProperty. please use SetProperty
    setProperty = SetProperty
    getProperty = GetProperty

    # private members
    width = 0
    height = 0
    mmf = 0
    usingMmf = True
    debugImagesFolder = "D:\\DebugImages\\"
    connected = False
    cameras = None
    currCamera = ""
    refreshProperties = True
    exposureTime = 1
    host = 0
    port = 0
    read_only = False

    # command lists
    LIST_CAMERAS = 0
    LIST_PROPERTIES = 1
    LIST_ALLOWED_VALUES = 2
    GET_PROPERTY = 3
    SET_PROPERTY = 4
    GET_IMAGE_16U = 5
    GET_IMAGE_32F = 10
    STOP_ACQUISITION = 11
    GET_RESULT = 14
    START_ACQUISITION = 15
    SET_HW_ROI = 16
    SET_SW_ROI = 17
    GET_MOVIE_BUFFER_INFO = 18
    GET_MOVIE_BUFFER = 19
    SET_PROPERTY_AND_GET_CHANGED_PROPERTIES = 20
    SET_HW_ROI_AND_GET_CHANGED_PROPERTIES = 21
    SET_SW_ROI_AND_GET_CHANGED_PROPERTIES = 22
    SET_VIRTUAL_MASK = 23
    SAVE_FINAL_AFTER_ACQ = 24
    SET_ENG_MODE = 25
    SET_ENG_MODE_GET_CHANGED_PROPERTIES = 26
    SET_SCAN_SIZE = 27
    SET_SCAN_ROI = 28
    SET_SCAN_SIZE_AND_GET_CHANGED_PROPERTIES = 29
    SET_SCAN_ROI__AND_GET_CHANGED_PROPERTIES = 30
    SET_CLIENT_READ_ONLY = 31


MMF_DATA_HEADER_SIZE = 24
MMF_IMAGE_BUFFER_SIZE = 8192 * 16384 * 4
MMF_DATA_BUFFER_SIZE = MMF_IMAGE_BUFFER_SIZE + MMF_DATA_HEADER_SIZE
