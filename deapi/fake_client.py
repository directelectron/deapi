# File containg the Client for connecting to the DE-Server
#
# Last update: 2024-08-07
# cfrancis@directelectron.com


# Python System imports
import socket
import sys
import struct
import logging
import re

import numpy as np

from deapi.buffer_protocols import pb
from deapi.version import version
from deapi import Client
import json
from importlib import resources

import deapi

inp_file = resources.files(deapi) / 'prop_dump.json'


versionInfo = list(map(int, version.split(".")))

## the commandInfo contains [VERSION_MAJOR.VERSION_MINOR.VERSION_PATCH.VERSION_REVISION]
commandVersion = (versionInfo[0] - 4) * 10 + versionInfo[1]
logLevel = logging.DEBUG
logLevel = logging.INFO
logLevel = logging.WARNING
logging.basicConfig(format="%(asctime)s DE %(levelname)-8s %(message)s", level=logLevel)
log = logging.getLogger("DECameraClientLib")
log.info("Python    : " + sys.version.split("(")[0])
log.info("DEClient  : " + version)
log.info("CommandVer: " + str(commandVersion))
log.info("logLevel  : " + str(logging.getLevelName(logLevel)))


class FakeClient(Client):
    def __init__(self):
        with open(inp_file) as f:
            self._values = json.load(f)

    def connect(self, host="test", port=12345):
        """Connect to DE-Server
        """
        self.cameras = ["Fake Test Camera",]
        if logLevel == logging.DEBUG:
            log.debug("Available cameras: %s", self.cameras)

        self.currCamera = self.cameras[0]
        if logLevel == logging.DEBUG:
            log.debug("Current camera: %s", self.currCamera)

        self.connected = True
        self.host = "test"
        self.port = "12345"
        log.info("Connected to server: %s, port: %d", host, port)

        serverVersion = self.get_property("Server Software Version")
        serverVersion = re.findall(r"\d+", serverVersion)

        version = [int(part) for part in serverVersion[:4]]
        temp = version[2] + version[1] * 1000 + version[0] * 1000000
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
            self.connected = False
            log.info("Disconnected.")


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
        command = self._add_single_command(command_id, param)
        response = self._sendCommand(command)
        if response != False:
            return self.__getParameters(response.acknowledge[0])
        else:
            return False

    # add a new command (with optional label and parameter)
    def _add_single_command(self, command_id=None, label=None, params=None):
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
        if command is None:
            return False
        if command.command[0].command_id == self.GET_PROPERTY + commandVersion * 100:
            return self._fake_get_property(command)
        elif command.command[0].command_id == self.SET_PROPERTY + commandVersion * 100:
            return self._fake_set_property(command)
        elif command.command[0].command_id == self.LIST_PROPERTIES + commandVersion * 100:
            return self._fake_list_properties(command)
        elif command.command[0].command_id == self.LIST_ALLOWED_VALUES + commandVersion * 100:
            return self._fake_list_allowed_values(command)

    def _fake_list_allowed_values(self, command):
        acknowledge_return = pb.DEPacket()
        acknowledge_return.type = pb.DEPacket.P_ACKNOWLEDGE
        ack1 = acknowledge_return.acknowledge.add()
        ack1.command_id = command.command[0].command_id
        name = command.command[0].parameter[0].p_string
        prop_dict = self._values[name]

        str_mapping = {"value":"Value",
                       "category":"Category",
                       "data_type":"Data Type",
                       "value_type":"Value Type", }

        for key, value in str_mapping.items():
            param = ack1.parameter.add()
            if isinstance(prop_dict[key], bool):
                param.type = pb.AnyParameter.P_BOOL
                param.p_bool = prop_dict[key]
            elif isinstance(prop_dict[key], int):
                param.type = pb.AnyParameter.P_INT
                param.p_int = prop_dict[key]
            elif isinstance(prop_dict[key], float):
                param.type = pb.AnyParameter.P_FLOAT
                param.p_float = prop_dict[key]
            else:
                param.type = pb.AnyParameter.P_STRING
                param.p_string = prop_dict[key]

        return acknowledge_return

    def _fake_list_properties(self, command):
        acknowledge_return = pb.DEPacket()
        acknowledge_return.type = pb.DEPacket.P_ACKNOWLEDGE
        ack1 = acknowledge_return.acknowledge.add()
        ack1.command_id = command.command[0].command_id
        for key in self._values:
            string_param = ack1.parameter.add()
            string_param.type = pb.AnyParameter.P_STRING
            string_param.p_string = key
        return acknowledge_return

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
        else: # type == pb.AnyParameter.P_STRING:
            val = command.command[0].parameter[1].p_string
        self._values[name]["value"] = val
        return acknowledge_return

    def _fake_get_property(self, command):
        acknowledge_return = pb.DEPacket()
        acknowledge_return.type = pb.DEPacket.P_ACKNOWLEDGE
        ack1 = acknowledge_return.acknowledge.add()  # add the first acknowledge
        ack1.command_id = command.command[0].command_id
        name = command.command[0].parameter[0].p_string
        val = self._values[name]

        if val["data_type"] == "String":
            val = val["value"]
        elif val["data_type"] == "Integer":
            val = int(val["value"])
        elif val["data_type"] == "Float":
            val = float(val["value"])
        elif val["data_type"] == "Boolean":
            val = bool(val["value"])

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
        return acknowledge_return

    def __recvFromSocket(self, sock, bytes):
        timeout = self.exposureTime * 10 + 30
        startTime = self.GetTime()
        self.socket.settimeout(timeout)

        buffer = ""
        try:
            buffer = sock.recv(bytes)
        except:
            pass  # continue if more needed

        log.debug(
            " __recvFromSocket : %d of %d in %.1f ms",
            len(buffer),
            bytes,
            (self.GetTime() - startTime) * 1000,
        )
        total_len = len(buffer)

        if total_len < bytes:
            while total_len < bytes:
                loopTime = self.GetTime()
                try:
                    buffer += sock.recv(bytes)
                    log.debug(
                        " __recvFromSocket : %d bytes of %d in %.1f ms",
                        len(buffer),
                        bytes,
                        (self.GetTime() - loopTime) * 1000,
                    )

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


