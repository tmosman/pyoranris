"""SRS CIR/CFR TCP client (replaces srs_cir_tcp_plot.py matplotlib path).

xapp_srs_ind serves newline text on --srs-cir-tcp HOST:PORT:

    META collect_us sfn slot rnti ue_id Ng Nu n_fft peak_cfr_bin peak_cfr_mag
    CFR  collect_us sfn slot rnti ant n_bins i0 q0 i1 q1 ...

CIR is computed client-side: CIR = fftshift(abs(ifft(CFR_complex))).
This module is the TCP *client* (xApp is the server).
"""

from __future__ import annotations

import logging
import queue
import socket
import threading
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)

RECONNECT_MIN_SEC = 1.0
RECONNECT_MAX_SEC = 30.0


@dataclass
class SrsFrame:
    """One CFR indication + derived CIR magnitude."""

    collect_us: int
    sfn: int
    slot: int
    rnti: int
    ue_id: int
    ant: int
    n_fft: int
    peak_cfr_bin: int
    peak_cfr_mag: float
    cfr_mag: np.ndarray
    cir_mag: np.ndarray


def parse_meta_line(line: str) -> Optional[dict]:
    parts = line.strip().split()
    if len(parts) < 11 or parts[0] != "META":
        return None
    try:
        return {
            "collect_us": int(parts[1]),
            "sfn": int(parts[2]),
            "slot": int(parts[3]),
            "rnti": int(parts[4]),
            "ue_id": int(parts[5]),
            "Ng": int(parts[6]),
            "Nu": int(parts[7]),
            "n_fft": int(parts[8]),
            "peak_cfr_bin": int(parts[9]),
            "peak_cfr_mag": float(parts[10]),
        }
    except ValueError:
        return None


def parse_cfr_line(line: str) -> Optional[tuple[np.ndarray, dict]]:
    parts = line.strip().split()
    if len(parts) < 7 or parts[0] != "CFR":
        return None
    try:
        meta = {
            "collect_us": int(parts[1]),
            "sfn": int(parts[2]),
            "slot": int(parts[3]),
            "rnti": int(parts[4]),
            "ant": int(parts[5]),
        }
        n_bins = int(parts[6])
        iq = parts[7:]
        if len(iq) < 2 * n_bins:
            return None
        re = np.array([float(iq[2 * k]) for k in range(n_bins)], dtype=np.float64)
        im = np.array([float(iq[2 * k + 1]) for k in range(n_bins)], dtype=np.float64)
        return re + 1j * im, meta
    except ValueError:
        return None


def cfr_to_cir(
    cfr: np.ndarray,
    *,
    n_fft_hint: int | None = None,
    fft_size: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (cfr_magnitude, cir_magnitude) with fftshifted CIR."""
    if fft_size is not None and fft_size > 0:
        n_fft = int(fft_size)
    elif n_fft_hint is not None and n_fft_hint > 0:
        n_fft = int(n_fft_hint)
    else:
        n_fft = len(cfr)
    if n_fft < len(cfr):
        n_fft = len(cfr)
    padded = np.zeros(n_fft, dtype=np.complex128)
    padded[: len(cfr)] = cfr
    cir = np.fft.fftshift(np.abs(np.fft.ifft(padded)))
    return np.abs(cfr), cir


class SrsCirTcpClient:
    """Background reconnecting client; queue holds latest SrsFrame samples."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8082,
        *,
        fft_size: int | None = None,
        maxsize: int = 64,
    ):
        self.host = host
        self.port = int(port)
        self.fft_size = fft_size
        self.data_queue: queue.Queue = queue.Queue(maxsize=maxsize)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.connected = False
        self.last_error = ""
        self.frames_received = 0
        self._meta: dict = {}

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="srs-cir-tcp")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        self.connected = False

    def _put_frame(self, frame: SrsFrame) -> None:
        try:
            self.data_queue.put_nowait(frame)
        except queue.Full:
            try:
                _ = self.data_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.data_queue.put_nowait(frame)
            except queue.Full:
                pass

    def _handle_line(self, line: str) -> None:
        meta = parse_meta_line(line)
        if meta is not None:
            self._meta.update(meta)
            return
        row = parse_cfr_line(line)
        if row is None:
            return
        cfr, cfr_meta = row
        self._meta.update(cfr_meta)
        n_fft_hint = self._meta.get("n_fft")
        hint = int(n_fft_hint) if isinstance(n_fft_hint, int) else None
        cfr_mag, cir_mag = cfr_to_cir(cfr, n_fft_hint=hint, fft_size=self.fft_size)
        frame = SrsFrame(
            collect_us=int(self._meta.get("collect_us", cfr_meta["collect_us"])),
            sfn=int(self._meta.get("sfn", cfr_meta["sfn"])),
            slot=int(self._meta.get("slot", cfr_meta["slot"])),
            rnti=int(self._meta.get("rnti", cfr_meta["rnti"])),
            ue_id=int(self._meta.get("ue_id", 0)),
            ant=int(cfr_meta["ant"]),
            n_fft=int(hint or len(cfr)),
            peak_cfr_bin=int(self._meta.get("peak_cfr_bin", -1)),
            peak_cfr_mag=float(self._meta.get("peak_cfr_mag", float("nan"))),
            cfr_mag=cfr_mag,
            cir_mag=cir_mag,
        )
        self.frames_received += 1
        self._put_frame(frame)

    def _run(self) -> None:
        delay = RECONNECT_MIN_SEC
        while not self._stop.is_set():
            try:
                sock = socket.create_connection((self.host, self.port), timeout=30.0)
            except OSError as exc:
                self.connected = False
                self.last_error = str(exc)
                log.warning("SRS CIR connect failed: %s; retry in %.0fs", exc, delay)
                if self._stop.wait(delay):
                    break
                delay = min(delay * 1.5, RECONNECT_MAX_SEC)
                continue

            delay = RECONNECT_MIN_SEC
            self.connected = True
            self.last_error = ""
            log.info("SRS CIR connected to %s:%s", self.host, self.port)
            try:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except OSError:
                pass
            sock.settimeout(0.5)
            buf = b""
            try:
                while not self._stop.is_set():
                    try:
                        chunk = sock.recv(65536)
                    except socket.timeout:
                        continue
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        raw, buf = buf.split(b"\n", 1)
                        line = raw.decode("utf-8", errors="replace")
                        try:
                            self._handle_line(line)
                        except Exception:
                            log.exception("SRS line parse failed")
            finally:
                self.connected = False
                try:
                    sock.close()
                except OSError:
                    pass
                if self._stop.is_set():
                    break
                log.warning("SRS CIR disconnected; retry in %.0fs", delay)
                if self._stop.wait(delay):
                    break
                delay = min(delay * 1.5, RECONNECT_MAX_SEC)
