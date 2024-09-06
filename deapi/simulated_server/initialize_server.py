import sys

from fake_server import FakeServer
import socket
import struct
from deapi.buffer_protocols import pb
import logging
import sys
import time


# Defining main function
def main(port=13240):

    HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    PORT = port  # Port to listen on (non-privileged ports are > 1023)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        sys.stderr.write("started")
        sys.stderr.flush()
        while True:
            conn, addr = server_socket.accept()  # What waits for a connection
            server = FakeServer(socket=conn)
            connected = True
            while connected:
                try:
                    totallen = conn.recv(4)
                    totallenRecv = struct.unpack("I", totallen)[0]
                    message = conn.recv(totallenRecv)
                    message_packet = pb.DEPacket()
                    message_packet.ParseFromString(message)
                    response = server._respond_to_command(message_packet)

                    for r in response:
                        if isinstance(r, pb.DEPacket):
                            packet = (
                                struct.pack("I", r.ByteSize()) + r.SerializeToString()
                            )
                            conn.send(packet)
                        else:
                            conn.sendall(r)
                except:
                    connected = False


# Using the special variable
# __name__
if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(int(sys.argv[1]))
    else:
        main()
