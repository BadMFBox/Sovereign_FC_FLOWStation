"""burner_ipc.py — Unix socket IPC for Burner Gate"""
import os
import socket
import struct
import threading
from enum import IntEnum

BURNER_SOCKET_PATH = "/tmp/burner_gate.sock"
FRAME_HEADER_SIZE  = 5


class OpCode(IntEnum):
    PING           = 0x01
    PONG           = 0x02
    TOKEN_REQUEST  = 0x10
    TOKEN_RESPONSE = 0x11
    WIPE_REQUEST   = 0x20
    WIPE_RESPONSE  = 0x21
    BURN_SIGNAL    = 0x30
    ERROR          = 0xFF


class Frame:
    __slots__ = ("opcode", "payload")

    def __init__(self, opcode: OpCode, payload: bytes = b""):
        self.opcode  = opcode
        self.payload = payload

    def encode(self) -> bytes:
        return struct.pack(">BI", int(self.opcode), len(self.payload)) + self.payload

    @staticmethod
    def decode(data: bytes):
        if len(data) < FRAME_HEADER_SIZE:
            raise ValueError("Frame too short")
        opcode, length = struct.unpack(">BI", data[:FRAME_HEADER_SIZE])
        payload = data[FRAME_HEADER_SIZE: FRAME_HEADER_SIZE + length]
        return Frame(OpCode(opcode), payload)


class BurnerConnection:
    def __init__(self, conn: socket.socket):
        self._conn = conn

    def send_frame(self, frame: Frame):
        self._conn.sendall(frame.encode())

    def recv_frame(self) -> Frame:
        hdr     = self._recv_exact(FRAME_HEADER_SIZE)
        opcode, length = struct.unpack(">BI", hdr)
        payload = self._recv_exact(length) if length else b""
        return Frame(OpCode(opcode), payload)

    def _recv_exact(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self._conn.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Connection closed")
            buf += chunk
        return buf

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


class BurnerServer:
    def __init__(self, socket_path: str, hmac_key: bytes, handler):
        self._path    = socket_path
        self._key     = hmac_key
        self._handler = handler
        self._sock    = None
        self._running = False

    def start(self):
        if os.path.exists(self._path):
            os.unlink(self._path)
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(self._path)
        self._sock.listen(5)
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True, name="burner-ipc").start()

    def _accept_loop(self):
        while self._running:
            try:
                self._sock.settimeout(1.0)
                try:
                    conn, _ = self._sock.accept()
                except socket.timeout:
                    continue
                threading.Thread(target=self._handle_conn, args=(conn,), daemon=True).start()
            except Exception:
                pass

    def _handle_conn(self, conn):
        bc = BurnerConnection(conn)
        try:
            while True:
                frame = bc.recv_frame()
                self._handler(bc, frame)
        except Exception:
            pass
        finally:
            bc.close()

    def stop(self):
        self._running = False
        try:
            self._sock.close()
        except Exception:
            pass
        try:
            if os.path.exists(self._path):
                os.unlink(self._path)
        except Exception:
            pass
