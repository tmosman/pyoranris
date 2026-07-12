"""KPM MAC RSRP/SINR TCP client (replaces mac_rsrp_tcp_plot.py matplotlib path).

xapp_kpm_moni serves newline text on --mac-rsrp-tcp HOST:PORT:

    collectStartTime_us ran_ue_id mac_avg_rsrp_dBm mac_avg_sinr_dB

Sentinel -1000 = missing. This module is the TCP *client* (xApp is the server).
"""

from __future__ import annotations

import logging
import math
import queue
import socket
import threading
import time
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)

SENTINEL = -1000.0
RECONNECT_MIN_SEC = 1.0
RECONNECT_MAX_SEC = 30.0


@dataclass
class MacKpiSample:
    collect_us: int
    ran_ue: int
    rsrp: float
    sinr: float
    t_rel_s: float = 0.0


def parse_data_line(line: str) -> Optional[tuple[int, int, float, float]]:
    """Return (collect_us, ran_ue, rsrp_dbm, snr_db). Legacy 3-column: SNR is NaN."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = line.split()
    if len(parts) == 3:
        try:
            return int(parts[0]), int(parts[1]), float(parts[2]), float("nan")
        except ValueError:
            return None
    if len(parts) == 4:
        try:
            return int(parts[0]), int(parts[1]), float(parts[2]), float(parts[3])
        except ValueError:
            return None
    return None


def _map_sentinel(value: float) -> float:
    if math.isnan(value):
        return value
    if abs(value - SENTINEL) < 1e-6:
        return float("nan")
    return float(value)


class MacRsrpTcpClient:
    """Background reconnecting client that fills ``data_queue`` with MacKpiSample."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8081, maxsize: int = 4096):
        self.host = host
        self.port = port
        self.data_queue: queue.Queue = queue.Queue(maxsize=maxsize)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.connected = False
        self.last_error = ""
        self._t0_collect: int | None = None
        self.last_ran_ue = 0
        self.samples_received = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()
        log.info("MAC RSRP client connecting to %s:%s", self.host, self.port)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        self.connected = False

    def _push(self, sample: MacKpiSample) -> None:
        try:
            self.data_queue.put_nowait(sample)
        except queue.Full:
            try:
                self.data_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.data_queue.put_nowait(sample)
            except queue.Full:
                pass

    def _reader_loop(self) -> None:
        reconnect_delay = RECONNECT_MIN_SEC
        while not self._stop.is_set():
            buf = b""
            try:
                sock = socket.create_connection((self.host, self.port), timeout=30.0)
            except OSError as exc:
                self.connected = False
                self.last_error = str(exc)
                log.warning(
                    "MAC RSRP connect failed: %s; retry in %.0fs", exc, reconnect_delay
                )
                if self._stop.wait(reconnect_delay):
                    break
                reconnect_delay = min(reconnect_delay * 1.5, RECONNECT_MAX_SEC)
                continue

            reconnect_delay = RECONNECT_MIN_SEC
            self.connected = True
            self.last_error = ""
            log.info("MAC RSRP connected to %s:%s", self.host, self.port)
            try:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except OSError:
                pass
            sock.settimeout(0.5)
            try:
                while not self._stop.is_set():
                    try:
                        chunk = sock.recv(16384)
                    except socket.timeout:
                        continue
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        raw, buf = buf.split(b"\n", 1)
                        line = raw.decode("utf-8", errors="replace")
                        row = parse_data_line(line)
                        if row is None:
                            continue
                        collect_us, ran_ue, rsrp, snr = row
                        if self._t0_collect is None:
                            self._t0_collect = collect_us
                        sample = MacKpiSample(
                            collect_us=collect_us,
                            ran_ue=ran_ue,
                            rsrp=_map_sentinel(rsrp),
                            sinr=_map_sentinel(snr),
                            t_rel_s=(collect_us - self._t0_collect) * 1e-6,
                        )
                        self.last_ran_ue = ran_ue
                        self.samples_received += 1
                        self._push(sample)
            finally:
                self.connected = False
                try:
                    sock.close()
                except OSError:
                    pass
                if self._stop.is_set():
                    break
                log.warning(
                    "MAC RSRP disconnected; retry in %.0fs", reconnect_delay
                )
                if self._stop.wait(reconnect_delay):
                    break
                reconnect_delay = min(reconnect_delay * 1.5, RECONNECT_MAX_SEC)
