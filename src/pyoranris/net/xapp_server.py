"""xApp KPI TCP server (binary RSRP / DL / UL ingest)."""

from __future__ import annotations

import logging
import queue
import socket
import struct
import threading

log = logging.getLogger(__name__)


class XAppServer:
    """Accepts xApp connections and pushes [RSRP, DL_Mbps, UL_Mbps] into a LIFO queue."""

    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.server_socket: socket.socket | None = None
        self.clients: list[socket.socket] = []
        self.server_thread: threading.Thread | None = None
        self.running = False
        self.KPIs = [None, None, None]
        self.data_queue: queue.LifoQueue = queue.LifoQueue(maxsize=2)

    def start_server(self) -> None:
        if self.running:
            log.info("xApp server already running")
            return
        self.running = True
        self.server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.server_thread.start()
        log.info("xApp server thread started at %s:%s", self.ip, self.port)

    def run_server(self) -> None:
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.ip, self.port))
            self.server_socket.listen()
            log.info("xApp server listening on %s:%s", self.ip, self.port)
            self.accept_clients()
        except Exception:
            log.exception("xApp server start error")
            self.running = False
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
                    log.info("xApp connection from %s", client_address)
                    self.clients.append(client_socket)
                    threading.Thread(
                        target=self.handle_client, args=(client_socket,), daemon=True
                    ).start()
                except socket.timeout:
                    continue
        except Exception:
            if self.running:
                log.exception("Error accepting xApp clients")
        finally:
            for client in self.clients:
                try:
                    client.close()
                except OSError:
                    pass
            self.clients = []

    def _enqueue_kpi(self, kpis: list) -> None:
        payload = list(kpis)
        try:
            self.data_queue.put_nowait(payload)
        except queue.Full:
            try:
                self.data_queue.get_nowait()
            except queue.Empty:
                pass
            self.data_queue.put_nowait(payload)
        self.KPIs = payload

    def handle_client(self, client_socket: socket.socket) -> None:
        try:
            while self.running:
                data = client_socket.recv(80)
                if not data:
                    log.info("xApp peer closed connection")
                    break
                unpacked = struct.unpack("iiii", data[:16])
                rsrp = unpacked[1]
                dl_thr = unpacked[3] / 1000
                ul_thr = unpacked[2] / 1000
                self._enqueue_kpi([rsrp, dl_thr, ul_thr])
        except OSError:
            if self.running:
                log.debug("xApp client socket closed", exc_info=True)
        except Exception:
            log.exception("Error handling xApp client")
        finally:
            try:
                client_socket.close()
            except OSError:
                pass
            self.clients = [c for c in self.clients if c is not client_socket]
            log.info("xApp client disconnected")

    def drain_queue(self) -> None:
        while True:
            try:
                self.data_queue.get_nowait()
            except queue.Empty:
                break

    def stop_server(self) -> None:
        self.running = False
        for client in list(self.clients):
            try:
                client.close()
            except OSError:
                pass
        self.clients = []
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        log.info("xApp server shutdown initiated")


# Back-compat name from legacy
xAppServer = XAppServer
