"""Camera bounding-box TCP server (JSON dict ingest)."""

from __future__ import annotations

import json
import logging
import queue
import socket
import threading

log = logging.getLogger(__name__)


class CameraTCPServer:
    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.server_socket: socket.socket | None = None
        self.clients: list[socket.socket] = []
        self.server_thread: threading.Thread | None = None
        self.running = False
        self.data_queue: queue.LifoQueue = queue.LifoQueue()
        self.queue_buffer = 1000
        self.num_iteration = 0

    def start_server(self) -> None:
        if self.running:
            return
        self.server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.server_thread.start()
        self.running = True
        log.info("Camera server started at %s:%s", self.ip, self.port)

    def run_server(self) -> None:
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.ip, self.port))
            self.server_socket.listen(5)
            self.accept_clients()
        except Exception:
            log.exception("Camera server start error")
        finally:
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None

    def accept_clients(self) -> None:
        try:
            while self.running and self.server_socket:
                self.server_socket.settimeout(0.1)
                try:
                    client_socket, client_address = self.server_socket.accept()
                    self.clients.append(client_socket)
                    threading.Thread(
                        target=self.handle_client, args=(client_socket,), daemon=True
                    ).start()
                except socket.timeout:
                    continue
        except Exception:
            if self.running:
                log.exception("Camera accept error")
        finally:
            for client in self.clients:
                client.close()
            self.clients = []

    def handle_client(self, client_socket: socket.socket) -> None:
        try:
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    continue
                received = json.loads(data.decode("utf-8"))
                self.data_queue.put(received)
                self.num_iteration += 1
                if self.num_iteration > self.queue_buffer:
                    with self.data_queue.mutex:
                        self.data_queue.queue.clear()
                        self.num_iteration = 0
        except Exception:
            log.exception("Camera client error")
        finally:
            client_socket.close()

    def stop_server(self) -> None:
        self.running = False
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
