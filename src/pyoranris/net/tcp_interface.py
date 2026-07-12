"""Generic TCP client used by unit tests and simple backends."""

from __future__ import annotations

import logging
import socket
import threading

log = logging.getLogger(__name__)


class TCPInterface:
    def __init__(self, host: str, port: int, timeout: float = 2.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self.lock = threading.Lock()

    def connect(self) -> None:
        with self.lock:
            if self.sock:
                return
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            s.connect((self.host, self.port))
            self.sock = s
            log.info("Connected to %s:%s", self.host, self.port)

    def send(self, data: bytes) -> None:
        if not self.sock:
            self.connect()
        with self.lock:
            assert self.sock is not None
            self.sock.sendall(data)

    def recv(self, n: int = 4096) -> bytes:
        if not self.sock:
            self.connect()
        assert self.sock is not None
        return self.sock.recv(n)

    def close(self) -> None:
        with self.lock:
            if self.sock:
                try:
                    self.sock.close()
                finally:
                    self.sock = None


# Alias matching historical naming in the demo
TCP_Interface = TCPInterface
