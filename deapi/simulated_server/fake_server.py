import time
import warnings

from deapi.buffer_protocols import pb
import json
from importlib import resources
import deapi
import numpy as np
from deapi.version import commandVersion
from deapi.fake_data.grains import TiltGrains
from skimage.transform import resize
from sympy import parse_expr

inp_file = resources.files(deapi) / "prop_dump.json"


def add_parameter(ack, value):
    """
    Add a parameter to a protobuffer
    """
    param = ack.parameter.add()
    if isinstance(value, str):
        param.type = pb.AnyParameter.P_STRING
        param.p_string = value
    elif isinstance(value, int):
        param.type = pb.AnyParameter.P_INT
        param.p_int = value
    elif isinstance(value, bool):
        param.type = pb.AnyParameter.P_BOOL
        param.p_bool = value
    elif isinstance(value, float):
        param.type = pb.AnyParameter.P_FLOAT
        param.p_float = value
    else:
        raise ValueError(f"Value {value} not recognized of type {type(value)}")
    return ack


class Property:
    def __init__(
        self,
        name,
        value,
        data_type,
        category,
        value_type,
        options,
        default_value=None,
        set_expression=None,
        get_expression=None,
        set_also_expressions=None,
        server=None,
    ):
        self.name = name
        self.data_type = data_type
        self.category = category
        self.value_type = value_type
        self.options = options
        self.server = server
        self._value = value
        self.default_value = default_value
        self.set_expression = set_expression
        self.get_expression = get_expression
        self.set_also_expressions = set_also_expressions

    @property
    def value(self):
        if self.get_expression is not None:
            epr = parse_expr(self.get_expression)
            symbols = epr.free_symbols
            replace_dict = {}
            for s in symbols:
                if s == "value":
                    replace_dict[s] = self._value
                else:
                    replace_dict[s] = self.server[s]
            value = epr.evalf(subs=replace_dict)
            if self.data_type == "Integer":
                value = int(value)
            elif self.data_type == "Float":
                value = float(value)
            elif self.data_type == "String":
                value = str(value)
            value = str(value)
            self._value = value
            return value
        elif self.category == "Server":
            return getattr(self.server, self.name.replace(" ", "_").lower())
        else:
            return self._value

    @value.setter
    def value(self, value):
        if self.set_expression is not None:
            epr = parse_expr(self.set_expression)
            symbols = epr.free_symbols
            replace_dict = {}
            for s in symbols:
                if str(s) == "value":
                    replace_dict[s] = value
                else:
                    replace_dict[s] = self.server[s]
            value = epr.evalf(subs=replace_dict)
        elif self.value_type == "READ_ONLY" or self.value_type == "Server":
            warnings.warn(f"Property {self.name} is read only")
            value = self._value
        elif self.value_type == "Range" and self.options is not None:
            range = np.array(self.options.split(",")[:2]).astype(float)
            if float(value) < range[0] or float(value) > range[1]:
                warnings.warn(f"Value {value} not in range {range}")
                value = self._value
        elif self.value_type == "Set" and self.options is not None:
            op = [
                o.replace("*", "").replace("'", "").strip()
                for o in self.options.split(",")
            ]
            if str(value) not in op:
                warnings.warn(f"Value {value} not in options {self.options}")
                value = self._value

        if self.data_type == "Integer":
            value = int(value)
        elif self.data_type == "Float":
            value = float(value)
        elif self.data_type == "String":
            value = str(value)
        self._value = str(value)

        if self.set_also_expressions is not None:
            for parameter, expr in self.set_also_expressions.items():
                epr = parse_expr(expr)
                symbols = epr.free_symbols
                replace_dict = {}
                for s in symbols:
                    if s == "value":
                        replace_dict[s] = value
                    else:
                        replace_dict[s] = self.server[s]
                ans = epr.evalf(subs=replace_dict)
                self.server[parameter] = ans


class FakeServer:
    def __init__(self, dataset="grains", socket=None):
        self.start_time = time.time()
        self.end_time = time.time()
        self.has_movie_buffer = False
        self.movie_buffer_index = 0
        self.dataset = dataset
        self.fake_data = None
        self.socket = socket
        self.current_movie_index = 0

        with open(inp_file) as f:
            values = json.load(f)
            property_dict = {}
            for v in values:
                new_v = v.replace(" ", "_").lower().replace("(", "").replace(")", "")
                property_dict[new_v] = Property(
                    name=v,
                    value=values[v]["value"],
                    data_type=values[v]["data_type"],
                    category=values[v]["category"],
                    value_type=values[v]["value_type"],
                    options=values[v]["options"],
                    default_value=values[v]["default_value"],
                    server=self,
                    set_expression=values[v].get("set", None),
                    get_expression=values[v].get("get", None),
                    set_also_expressions=values[v].get("set_also", None),
                )
        self._values = property_dict
        self._number_of_frames_requested = 0

        self.current_socket_result = None
        self._values["acquisition_status"] = Property(
            name="Acquisition Status",
            value="Idle",
            data_type="String",
            category="Server",
            value_type="Set",
            options=["Idle", "Acquiring"],
            server=self,
        )
        self._values["number_of_frames_requested"] = Property(
            name="Number of Frames Requested",
            value="Idle",
            data_type="Integer",
            category="Server",
            value_type="Read Only",
            options=None,
            server=self,
        )

        self._values["remaining_number_of_acquisitions"] = Property(
            name="Remaining Number of Acquisitions",
            value="Idle",
            data_type="Integer",
            category="Server",
            value_type="Read Only",
            options=None,
            server=self,
        )

        self.virtual_masks = []
        for i in range(4):
            self.virtual_masks.append(
                np.ones(
                    shape=(
                        int(self["Image Size X (pixels)"]),
                        int(self["Image Size Y (pixels)"]),
                    ),
                    dtype=np.int8,
                )
            )

    def __getitem__(self, item):
        if not isinstance(item, str):
            item = str(item)
        item = item.replace(" ", "_").lower().replace("(", "").replace(")", "")
        return self._values[item].value

    def __setitem__(self, key, value):
        key = key.replace(" ", "_").lower().replace("(", "").replace(")", "")
        self._values[key].value = value

    @property
    def acquisition_status(self):
        print("Getting acquisition status")
        print((time.time() < self.end_time))
        if time.time() < self.end_time:
            print("Acquiring")
            return "Acquiring"
        else:
            print("Idle")
            return "Idle"

    @property
    def number_of_frames_requested(self):
        if self["Scan - Enable"] == "On":
            return self["Scan - Size X"] * self["Scan - Size Y"]
        else:
            return self._number_of_frames_requested

    @property
    def remaining_number_of_acquisitions(self):
        if self.acquisition_status == "Idle":
            return 0
        if self.acquisition_status == "Acquiring":
            return 2  # for fake server we always return 2 acquisitions

    @number_of_frames_requested.setter
    def number_of_frames_requested(self, value):
        self._number_of_frames_requested = value

    @property
    def current_navigation_index(self):
        if self.fake_data is None:
            return ValueError("No fake data initialized")
        if self.acquisition_status == "Idle":
            return tuple(np.array(self.fake_data.navigator.shape) - 1)
        else:
            index = np.unravel_index(
                int(
                    (time.time() - self.start_time) * float(self["Frames Per Second"]),
                ),
                self.fake_data.navigator.shape,
            )  # only works for raster scans
            return index

    def _respond_to_command(self, command=None):
        if command is None:
            return False
        if command.command[0].command_id == self.GET_PROPERTY + commandVersion * 100:
            return self._fake_get_property(command)
        elif command.command[0].command_id == self.SET_PROPERTY + commandVersion * 100:
            return self._fake_set_property(command)
        elif (
            command.command[0].command_id == self.LIST_PROPERTIES + commandVersion * 100
        ):
            return self._fake_list_properties(command)
        elif (
            command.command[0].command_id
            == self.LIST_ALLOWED_VALUES + commandVersion * 100
        ):
            return self._fake_list_allowed_values(command)
        elif (
            command.command[0].command_id
            == self.GET_MOVIE_BUFFER_INFO + commandVersion * 100
        ):
            return self._fake_get_movie_buffer_info(command)
        elif (
            command.command[0].command_id
            == self.GET_MOVIE_BUFFER + commandVersion * 100
        ):
            return self._fake_get_movie_buffer(command)
        elif (
            command.command[0].command_id
            == self.START_ACQUISITION + commandVersion * 100
        ):
            return self._fake_start_acquisition(command)
        elif command.command[0].command_id == self.GET_RESULT + commandVersion * 100:
            return self._fake_get_result(command)
        elif command.command[0].command_id == self.LIST_CAMERAS + commandVersion * 100:
            return self._fake_list_cameras(command)
        elif (
            command.command[0].command_id
            == self.SET_CLIENT_READ_ONLY + commandVersion * 100
        ):
            return self._fake_set_client_read_only(command)
        elif (
            command.command[0].command_id
            == self.SET_VIRTUAL_MASK + commandVersion * 100
        ):
            return self._fake_set_virtual_mask(command)
        else:
            raise NotImplementedError(
                f"Command {command.command[0].command_id} not implemented"
                f" in the FakeServer. Please use the real DEServer for testing."
                f" The commandVersion is {commandVersion}"
            )

    def _fake_set_client_read_only(self, command):

        self.is_read_only = command.command[0].parameter[0].p_bool
        acknowledge_return = pb.DEPacket()
        acknowledge_return.type = pb.DEPacket.P_ACKNOWLEDGE
        ack1 = acknowledge_return.acknowledge.add()
        ack1.command_id = command.command[0].command_id
        return (acknowledge_return,)

    def _fake_set_virtual_mask(self, command):
        acknowledge_return = pb.DEPacket()
        acknowledge_return.type = pb.DEPacket.P_ACKNOWLEDGE
        ack1 = acknowledge_return.acknowledge.add()
        ack1.command_id = command.command[0].command_id

        mask_id = command.command[0].parameter[0].p_int
        w = command.command[0].parameter[1].p_int
        h = command.command[0].parameter[2].p_int
        print(f"Setting virtual mask {mask_id} with size {w}x{h}")

        total_bytes = w * h
        buffer = self.socket.recv(total_bytes)
        total_len = len(buffer)
        if total_len < total_bytes:
            while total_len < total_bytes:
                try:
                    buffer += self.socket.recv(total_bytes)
                    total_len = len(buffer)
                except self.socket.timeout:
                    raise ValueError("Socket timed out")
        buffer = buffer
        mask = np.frombuffer(buffer, dtype=np.int8).reshape((w, h))
        self.virtual_masks[mask_id] = mask
        print(f"Virtual mask {mask_id} set with {mask}")
        return (acknowledge_return,)

    def _fake_list_cameras(self, command):
        acknowledge_return = pb.DEPacket()
        acknowledge_return.type = pb.DEPacket.P_ACKNOWLEDGE
        ack1 = acknowledge_return.acknowledge.add()
        ack1.command_id = command.command[0].command_id
        add_parameter(ack1, "Fake Camera")
        return (acknowledge_return,)

    def _initialize_data(self, scan_size_x, scan_size_y, kx_pixels, ky_pixels):
        if self.dataset == "grains":
            self.fake_data = TiltGrains(
                x_pixels=scan_size_x,
                y_pixels=scan_size_y,
                kx_pixels=kx_pixels,
                ky_pixels=ky_pixels,
                server=self,
            )
        else:
            raise ValueError(
                f"Dataset {self.dataset} not recognized. Please use 'grains'"
            )

    def _fake_start_acquisition(self, command):
        self.current_movie_index = 0

        acknowledge_return = pb.DEPacket()
        num_acq = command.command[0].parameter[0].p_int
        if self["Scan - Enable"] == "On":
            frames = int(self["Scan - Size X"]) * int(self["Scan - Size Y"])
            self._initialize_data(
                int(self["Scan - Size X"]),
                int(self["Scan - Size Y"]),
                int(self["Sensor Size X (pixels)"]),
                int(self["Sensor Size X (pixels)"]),
            )
        else:
            self._initialize_data(
                int(4),
                int(4),
                int(self["Sensor Size X (pixels)"]),
                int(self["Sensor Size X (pixels)"]),
            )
            frames = num_acq
            self.number_of_frames_requested = frames
        fps = float(self["Frames Per Second"])
        total_time = frames * num_acq / fps
        self.start_time = time.time()
        print(f"Acquisition started for {total_time} seconds")
        print(f"Acquisition started at {self.start_time}")
        print(f"Acquisition will end at {self.start_time + total_time}")

        self.end_time = self.start_time + total_time
        acknowledge_return.type = pb.DEPacket.P_ACKNOWLEDGE
        ack1 = acknowledge_return.acknowledge.add()
        ack1.command_id = command.command[0].command_id
        return (acknowledge_return,)

    def _fake_list_allowed_values(self, command):
        acknowledge_return = pb.DEPacket()
        acknowledge_return.type = pb.DEPacket.P_ACKNOWLEDGE
        ack1 = acknowledge_return.acknowledge.add()
        ack1.command_id = command.command[0].command_id
        name = command.command[0].parameter[0].p_string
        prop_dict = self._values[
            name.replace(" ", "_").lower().replace("(", "").replace(")", "")
        ]

        list_props = [
            "data_type",
            "value_type",
            "category",
            "options",
            "default_value",
            "value",
        ]

        for key in list_props:
            param = ack1.parameter.add()
            if isinstance(getattr(prop_dict, key), bool):
                param.type = pb.AnyParameter.P_BOOL
                param.p_bool = getattr(prop_dict, key)
            elif isinstance(getattr(prop_dict, key), int):
                param.type = pb.AnyParameter.P_INT
                param.p_int = getattr(prop_dict, key)
            elif isinstance(getattr(prop_dict, key), float):
                param.type = pb.AnyParameter.P_FLOAT
                param.p_float = getattr(prop_dict, key)
            else:
                param.type = pb.AnyParameter.P_STRING
                param.p_string = getattr(prop_dict, key)

        return (acknowledge_return,)

    def _fake_list_properties(self, command):
        acknowledge_return = pb.DEPacket()
        acknowledge_return.type = pb.DEPacket.P_ACKNOWLEDGE
        ack1 = acknowledge_return.acknowledge.add()
        ack1.command_id = command.command[0].command_id
        for key in self._values:
            string_param = ack1.parameter.add()
            string_param.type = pb.AnyParameter.P_STRING
            string_param.p_string = self._values[key].name
        return (acknowledge_return,)

    def _fake_set_property(self, command):
        acknowledge_return = pb.DEPacket()
        acknowledge_return.type = pb.DEPacket.P_ACKNOWLEDGE
        ack1 = acknowledge_return.acknowledge.add()
        ack1.command_id = command.command[0].command_id
        name = command.command[0].parameter[0].p_string
        type = command.command[0].parameter[1].type
        if type == pb.AnyParameter.P_BOOL:
            val = command.command[0].parameter[1].p_bool
        elif type == pb.AnyParameter.P_INT:
            val = command.command[0].parameter[1].p_int
        elif type == pb.AnyParameter.P_FLOAT:
            val = command.command[0].parameter[1].p_float
        else:  # type == pb.AnyParameter.P_STRING:
            val = command.command[0].parameter[1].p_string
        name = name.replace(" ", "_").lower().replace("(", "").replace(")", "")
        self._values[name].value = val
        return (acknowledge_return,)

    def _fake_get_property(self, command):
        acknowledge_return = pb.DEPacket()
        acknowledge_return.type = pb.DEPacket.P_ACKNOWLEDGE
        ack1 = acknowledge_return.acknowledge.add()  # add the first acknowledge
        ack1.command_id = command.command[0].command_id
        name = command.command[0].parameter[0].p_string
        name = name.replace(" ", "_").lower().replace("(", "").replace(")", "")
        val = self._values.get(name, "Not Implemented")

        if val.data_type == "String":
            val = val.value
        elif val.data_type == "Integer":
            val = int(val.value)
        elif val.data_type == "Float":
            val = float(val.value)
        elif val.data_type == "Boolean":
            val = bool(val.value)

        if isinstance(val, bool):
            bool_param = acknowledge_return.acknowledge[0].parameter.add()
            bool_param.type = pb.AnyParameter.P_BOOL
            bool_param.p_bool = val
        elif isinstance(val, int) or isinstance(val, np.int32):
            int_param = acknowledge_return.acknowledge[0].parameter.add()
            int_param.type = pb.AnyParameter.P_INT
            int_param.p_int = val
        elif isinstance(val, float):
            float_param = acknowledge_return.acknowledge[0].parameter.add()
            float_param.type = pb.AnyParameter.P_FLOAT
            float_param.p_float = val
        else:
            string_param = acknowledge_return.acknowledge[0].parameter.add()
            string_param.type = pb.AnyParameter.P_STRING
            string_param.p_string = val
        return (acknowledge_return,)

    def _fake_get_movie_buffer_info(self, command):
        print("Getting movie buffer info")
        acknowledge_return = pb.DEPacket()
        acknowledge_return.type = pb.DEPacket.P_ACKNOWLEDGE
        ack1 = acknowledge_return.acknowledge.add()

        ack1.command_id = command.command[0].command_id
        int_param = ack1.parameter.add()
        int_param.type = pb.AnyParameter.P_INT
        int_param.p_int = 1024  # Header bytes
        int_param = ack1.parameter.add()
        int_param.type = pb.AnyParameter.P_INT
        int_param.p_int = (
            int(self["Image Size Y (pixels)"])
            * int(self["Image Size X (pixels)"])
            * int(self["Grabbing - Frames Per Buffer"])
            * 2
        )  # Image buffer bytes
        int_param = ack1.parameter.add()
        int_param.type = pb.AnyParameter.P_INT
        int_param.p_int = 0  # Frame index start pos
        int_param = ack1.parameter.add()
        int_param.type = pb.AnyParameter.P_INT
        int_param.p_int = int(self["Image Size X (pixels)"])  # image width
        int_param = ack1.parameter.add()
        int_param.type = pb.AnyParameter.P_INT
        int_param.p_int = 1024  # image start
        int_param = ack1.parameter.add()
        int_param.type = pb.AnyParameter.P_INT
        int_param.p_int = int(self["Image Size Y (pixels)"])  # image height
        int_param = ack1.parameter.add()
        int_param.type = pb.AnyParameter.P_INT
        int_param.p_int = int(self["Grabbing - Frames Per Buffer"])  # frames in buffer
        int_param = ack1.parameter.add()
        int_param.type = pb.AnyParameter.P_INT
        int_param.p_int = 5  # data type (only int16 supported)

        return (acknowledge_return,)

    def _fake_get_result(self, command):
        acknowledge_return = pb.DEPacket()
        acknowledge_return.type = pb.DEPacket.P_ACKNOWLEDGE
        ack1 = acknowledge_return.acknowledge.add()
        ack1.command_id = command.command[0].command_id
        frame_type = command.command[0].parameter[0].p_int
        pixel_format = command.command[0].parameter[1].p_int
        center_x = command.command[0].parameter[2].p_int
        center_y = command.command[0].parameter[3].p_int
        zoom = command.command[0].parameter[4].p_float
        windowWidth = command.command[0].parameter[5].p_int
        windowHeight = command.command[0].parameter[6].p_int
        fft = command.command[0].parameter[7].p_int
        stretchType = command.command[0].parameter[8].p_int
        stretch_min = command.command[0].parameter[9].p_float
        stretch_max = command.command[0].parameter[10].p_float
        stretch_gama = command.command[0].parameter[11].p_float
        outlier = command.command[0].parameter[12].p_float
        timeout = command.command[0].parameter[13].p_int
        histo_min = command.command[0].parameter[14].p_float
        histo_max = command.command[0].parameter[15].p_float
        histo_bins = command.command[0].parameter[16].p_int

        pixel_format_dict = {1: np.int8, 5: np.int16, 13: np.float32}

        if self.fake_data is None:
            self._initialize_data(
                scan_size_x=1,
                scan_size_y=1,
                kx_pixels=int(self["Sensor Size X (pixels)"]),
                ky_pixels=int(self["Sensor Size X (pixels)"]),
            )
        curr = self.current_navigation_index
        flat_index = int(np.ravel_multi_index(curr, self.fake_data.navigator.shape))
        if 2 < frame_type < 8:
            if self["Exposure Mode"] == "Gain" or self["Exposure Mode"] == "Trial":
                image = np.random.poisson(
                    np.ones(
                        (
                            int(self["Sensor Size X (pixels)"]),
                            int(self["Sensor Size X (pixels)"]),
                        )
                    )
                    * 100
                ).astype(pixel_format_dict[pixel_format])
            elif self["Exposure Mode"] == "Dark":
                image = np.random.poisson(
                    np.ones(
                        (
                            int(self["Sensor Size X (pixels)"]),
                            int(self["Sensor Size X (pixels)"]),
                        )
                    )
                    * 1
                ).astype(pixel_format_dict[pixel_format])
            else:
                image = self.fake_data[self.current_navigation_index].astype(
                    pixel_format_dict[pixel_format]
                )
            result = image.tobytes()

        elif frame_type == 10 or frame_type == 9:  # SUMTOTAL or SUMINTERMEDIATE
            if self["Exposure Mode"] == "Gain" or self["Exposure Mode"] == "Trial":
                image = np.random.poisson(
                    np.ones(
                        (
                            int(self["Sensor Size X (pixels)"]),
                            int(self["Sensor Size X (pixels)"]),
                        )
                    )
                    * 10000
                ).astype(pixel_format_dict[pixel_format])
            elif self["Exposure Mode"] == "Dark":
                image = np.random.poisson(
                    np.ones(
                        (
                            int(self["Sensor Size X (pixels)"]),
                            int(self["Sensor Size X (pixels)"]),
                        )
                    )
                    * 1
                ).astype(pixel_format_dict[pixel_format])
            else:
                image = np.sum(self.fake_data.signal, axis=1).astype(
                    pixel_format_dict[pixel_format]
                )
            result = image.tobytes()
        elif 11 < frame_type < 17:  # virtual image
            image = self.virtual_masks[frame_type - 12]
            print(image)
            if image.shape != (windowWidth, windowHeight):
                image = resize(
                    image, (windowWidth, windowHeight), preserve_range=True
                ).astype(np.int8)
            result = image.tobytes()
        elif 17 <= frame_type < 22:
            image = self.virtual_masks[frame_type - 17]
            calculation_type = self[
                f"Scan - Virtual Detector {frame_type-17} Calculation"
            ]
            image = self.fake_data.get_virtual_image(image, method=calculation_type)
            image = image.astype(pixel_format_dict[pixel_format])
            result = image.tobytes()

        else:
            raise ValueError(f"Frame type {frame_type} not Supported in PythonDEServer")
        # map to right order...
        mean_img = np.mean(image)
        eppix = mean_img / 208
        eps = np.sum(image) / 208 * float(self["Frames Per Second"])
        eppixps = eppix * float(self["Frames Per Second"])
        response_mapping = [
            int(pixel_format),  # pix format 0
            int(windowWidth),  # window width 1
            int(windowHeight),  # window height 2
            "Test",  # name 3
            int(0),  # acquisition index 4
            bool(self.acquisition_status == "Acquiring"),  # status 5
            int(flat_index),  # frame number 6
            int(1),  # frame count 7
            float(0),  # image min 8
            float(2**15),  # image max 9
            float(100),  # image mean 10
            float(5),  # image std 11
            float(100),  # eppix 12
            float(1000),  # eps 13
            float(500),  # eppixps 14
            0.0,  # epa2 15
            float(500),  # eppixpf 16
            0.0,  # eppix_incident 17
            0.0,  # eps_incident 18
            0.0,  # eppixps_incident 19
            0.0,  # epa2_incident 20
            0.0,  # eppixpf_incident 21
            0.0,  # red sat warning 22
            0.0,  # orange sat warning 23
            0.0,  # saturation 24
            "2.187026",  # current time 25
            0.0,  # autoStretchMin 26
            0.0,  # autoStretchMax 27
            0.0,  # autoStretchGamma 28
            0.0,  # histogram min 29
            float(np.min(image)),  # histogram max 30
            float(np.max(image)),  # histogram upper local max 31
        ]
        for i in range(histo_bins):
            response_mapping.append(int(0))
        # Then histogram...
        for val in response_mapping:
            ack1 = acknowledge_return.acknowledge.add()
            add_parameter(ack1, val)
        ans = (acknowledge_return,)
        # add the data header packet for how many bytes are in the data
        pack = pb.DEPacket()
        pack.type = pb.DEPacket.P_DATA_HEADER

        pack.data_header.bytesize = len(result)
        ans += (pack,)
        ans += (result,)
        print(f"Sending result with size {pack.ByteSize()} and data size {len(result)}")

        return ans

    def _fake_get_movie_buffer(self, command):
        sizey = int(self["Image Size Y (pixels)"])
        sizex = int(self["Image Size X (pixels)"])
        frames_per_buffer = int(self["Grabbing - Frames Per Buffer"])

        acknowledge_return = pb.DEPacket()
        acknowledge_return.type = pb.DEPacket.P_ACKNOWLEDGE
        ack1 = acknowledge_return.acknowledge.add()
        ack1.command_id = command.command[0].command_id
        int_param = ack1.parameter.add()
        int_param.type = pb.AnyParameter.P_INT

        if np.prod(self.fake_data.navigator.shape) > self.current_movie_index:
            frame_numbers = np.arange(
                self.current_movie_index,
                self.current_movie_index + frames_per_buffer,
                dtype=np.int64,
            )
            print(f"Getting movie buffer {frame_numbers}")
            data = self.fake_data.flat[
                self.current_movie_index : self.current_movie_index + frames_per_buffer
            ]
            print(f"Data shape {data.shape}")
            self.current_movie_index = self.current_movie_index + frames_per_buffer
            if len(frame_numbers) < 128:
                frame_numbers = np.pad(
                    frame_numbers,
                    (0, 128 - len(frame_numbers)),
                    mode="constant",
                    constant_values=0,
                )

            int_param.p_int = 5  # okay
            int_param = ack1.parameter.add()
            int_param.type = pb.AnyParameter.P_INT
            int_param.p_int = np.prod(data.shape) * 2 + 1024  # Image total bytes
            # Image total bytes
            int_param = ack1.parameter.add()
            int_param.type = pb.AnyParameter.P_INT
            int_param.p_int = data.shape[0]  # Number of frames

            ans = (acknowledge_return,)
            ans += (frame_numbers.tobytes(), data.astype(np.int16).tobytes())
        else:
            int_param.p_int = 4  # finished
            int_param = ack1.parameter.add()
            int_param.type = pb.AnyParameter.P_INT
            int_param.p_int = 0  # Image total bytes
            # Image total bytes
            int_param = ack1.parameter.add()
            int_param.type = pb.AnyParameter.P_INT
            int_param.p_int = 0
            ans = (acknowledge_return,)

        return ans

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
