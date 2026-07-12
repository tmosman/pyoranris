"""Lab ACK-style TCP helpers migrated from classes_file.TCP_Interface."""

from __future__ import annotations

import json
import logging
import socket
import time

log = logging.getLogger(__name__)


class LabTCPClient:
    """Connect-per-call client for RIS / UE / xApp / Jetson ACK protocols."""

    def __init__(self, host_ip: str, port: int, timeout: float = 2.0):
        self.host_ip = host_ip
        self.port = port
        self.timeout = timeout

    def _transact(self, payload: str, wait_ack: bool = True) -> str:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(self.timeout)
        received = ""
        try:
            client.connect((self.host_ip, self.port))
            client.sendall(payload.encode())
            received = client.recv(1024).decode()
            if wait_ack:
                deadline = time.time() + self.timeout
                while "ACK" not in received and time.time() < deadline:
                    time.sleep(0.0001)
                    chunk = client.recv(1024).decode()
                    if not chunk:
                        break
                    received += chunk
        except OSError as exc:
            log.error("TCP error talking to %s:%s: %s", self.host_ip, self.port, exc)
        finally:
            client.close()
        return received

    def send_ris_noACK(self, text: str, k) -> None:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(self.timeout)
        try:
            client.connect((self.host_ip, self.port))
            client.sendall(f"{text}{k}".encode())
        finally:
            client.close()

    def get_ris_beam(self, text: str):
        received = self._transact(text, wait_ack=True)
        if "ACK" in received:
            return received[3:]
        return 0

    def send_ris_ACK(self, text: str, k):
        received = self._transact(f"{text}{k}", wait_ack=True)
        if "ACK" in received:
            return received[3:]
        if "IP" in received:
            return json.loads(received)
        return received

    def send_gps_ACK(self, text: str, k):
        received = self._transact(f"{text}{k}", wait_ack=True)
        if "Longitude" in received:
            return json.loads(received)
        return received

    def send_quectel_ACK(self, text: str, k):
        return self._transact(f"{text}{k}", wait_ack=True)

    def send_jetson_ACK(self, text: str, k):
        return self._transact(f"{text}{k}", wait_ack=True)

    def send_oai_ue_ACK(self, text: str, k):
        return self._transact(f"{text}{k}", wait_ack=True)
