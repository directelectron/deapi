import sys
import traceback

from deapi.simulated_server.fake_server import FakeServer
import socket
import struct
from deapi.buffer_protocols import pb
import argparse


def _recv_exact(conn, n):
    """Read exactly *n* bytes from *conn*, looping over partial reads.

    Returns the complete byte string, or raises ``ConnectionResetError`` if
    the peer closes the connection before all bytes arrive.  This is necessary
    because TCP is a stream protocol: a single ``recv(n)`` call may legally
    return anywhere from 1 to n bytes, and on macOS the loopback interface
    fragments packets far more aggressively than Linux does.
    """
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionResetError(
                f"Connection closed after {len(buf)} of {n} expected bytes"
            )
        buf += chunk
    return buf


# Defining main function
def main(port=13240):
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, help="Port to listen on")
    args, _ = parser.parse_known_args()
    if args.port:
        port = args.port

    HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    PORT = port  # Port to listen on (non-privileged ports are > 1023)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        # Allow the port to be reused immediately after the process exits
        # (avoids "Address already in use" / TIME_WAIT failures between test runs)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        sys.stdout.write("started .... \n\n")
        sys.stdout.flush()
        sys.stderr.write(
            "Waiting for a Connection to: \n"
            f"    Host: {HOST}\n"
            f"    Port: {PORT} \n"
        )
        sys.stderr.flush()
        while True:
            conn, addr = server_socket.accept()  # What waits for a connection
            server = FakeServer(socket=conn)
            connected = True
            while connected:
                try:
                    totallen = _recv_exact(conn, 4)
                    totallenRecv = struct.unpack("I", totallen)[0]
                    message = _recv_exact(conn, totallenRecv)
                    message_packet = pb.DEPacket()
                    message_packet.ParseFromString(message)
                    response = server._respond_to_command(message_packet)

                    for r in response:
                        if isinstance(r, pb.DEPacket):
                            packet = (
                                struct.pack("I", r.ByteSize()) + r.SerializeToString()
                            )
                            conn.sendall(packet)
                        else:
                            conn.sendall(r)
                except Exception:
                    traceback.print_exc(file=sys.stderr)
                    connected = False


# Using the special variable
# __name__
if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(int(sys.argv[1]))
    else:
        main()
