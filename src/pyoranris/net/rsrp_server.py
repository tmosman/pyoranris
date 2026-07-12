"""Simple line-oriented RSRP ingest server (for offline / simulated feeds)."""

from __future__ import annotations

import logging
import queue
import socket
import threading

log = logging.getLogger(__name__)


class SimpleTCPServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 10000):
        self.host = host
        self.port = port
        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.data_queue: queue.Queue = queue.Queue()

    def start_server(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()
        log.info("RSRP server started on %s:%d", self.host, self.port)

    def _serve(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen(1)
            s.settimeout(1.0)
            while not self.stop_event.is_set():
                try:
                    conn, addr = s.accept()
                    log.info("RSRP connection from %s", addr)
                    with conn:
                        conn.settimeout(1.0)
                        buffer = b""
                        while not self.stop_event.is_set():
                            try:
                                data = conn.recv(4096)
                                if not data:
                                    break
                                buffer += data
                                while b"\n" in buffer:
                                    line, buffer = buffer.split(b"\n", 1)
                                    txt = line.decode().strip()
                                    parts = [p.strip() for p in txt.split(",") if p.strip()]
                                    try:
                                        vals = tuple(float(p) for p in parts)
                                        self.data_queue.put(vals)
                                    except Exception:
                                        log.exception("Failed to parse RSRP data: %s", txt)
                            except socket.timeout:
                                continue
                except socket.timeout:
                    continue
                except Exception:
                    log.exception("RSRP server error")

    def stop_server(self) -> None:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)
        log.info("RSRP server stopped")
