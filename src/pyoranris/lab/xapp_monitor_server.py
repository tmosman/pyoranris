"""TCP monitor server for legacy xapp_kpm_rc (pyoranris GUI :5005 control plane).

Replaces the ad-hoc ``xApp_tcp_server.py`` in the flexric tree.

Commands (concatenated with optional trailing digit, e.g. ``START0``):
  START  — stop any running xapp_kpm_rc, launch a fresh one
  STOP   — stop managed xapp_kpm_rc (or force-kill orphans)
  STATUS — report ``[ACK] running`` or ``[ACK] stopped``
  EXIT   — stop xapp_kpm_rc only; **keep** this monitor server listening
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

log = logging.getLogger(__name__)

XAPP_COMM = "xapp_kpm_rc"
KILL_TIMEOUT_S = 2.0
STOP_TIMEOUT_S = 5.0


def _expand(path: str) -> str:
    return os.path.expanduser(os.path.expandvars(path))


class XappProcessManager:
    """Manage a single xapp_kpm_rc subprocess."""

    def __init__(self, xapp_bin: str, cwd: str | None = None):
        self.xapp_bin = _expand(xapp_bin)
        self.cwd = _expand(cwd) if cwd else None
        self._process: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def _xapp_pids(self, exclude: set[int] | None = None) -> list[int]:
        exclude = exclude or set()
        exclude.add(os.getpid())
        pids: list[int] = []
        try:
            for entry in os.listdir("/proc"):
                if not entry.isdigit():
                    continue
                pid = int(entry)
                if pid in exclude:
                    continue
                comm_path = f"/proc/{pid}/comm"
                try:
                    with open(comm_path, encoding="ascii", errors="ignore") as fh:
                        comm = fh.read().strip()
                except (FileNotFoundError, PermissionError, OSError):
                    continue
                if comm == XAPP_COMM:
                    pids.append(pid)
        except OSError as exc:
            log.warning("Could not scan /proc for %s: %s", XAPP_COMM, exc)
        return pids

    def kill_orphans(self) -> None:
        pids = self._xapp_pids()
        if not pids:
            return
        for pid in pids:
            log.info("Stopping orphan %s (PID %s)", XAPP_COMM, pid)
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except PermissionError:
                log.warning("No permission to signal PID %s", pid)
        deadline = time.time() + KILL_TIMEOUT_S
        while time.time() < deadline and self._xapp_pids():
            time.sleep(0.1)
        for pid in self._xapp_pids():
            log.info("Force-killing %s (PID %s)", XAPP_COMM, pid)
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except PermissionError:
                log.warning("No permission to kill PID %s", pid)

    def is_running(self) -> bool:
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return True
        return bool(self._xapp_pids())

    def _stop_managed(self) -> str:
        if self._process is not None and self._process.poll() is None:
            log.info("Stopping managed %s", XAPP_COMM)
            self._process.terminate()
            try:
                self._process.wait(timeout=STOP_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                log.warning("Managed %s did not exit; SIGKILL", XAPP_COMM)
                self._process.kill()
                self._process.wait(timeout=KILL_TIMEOUT_S)
            self._process = None
            return "[ACK] Stopped"
        return "[ACK] Force-stopped"

    def stop(self) -> str:
        with self._lock:
            msg = self._stop_managed()
        if msg == "[ACK] Force-stopped":
            self.kill_orphans()
        return msg

    def start(self) -> str:
        if not Path(self.xapp_bin).is_file():
            return f"[ERR] xApp binary not found: {self.xapp_bin}"
        with self._lock:
            self._stop_managed()
        self.kill_orphans()
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return "[ACK] Already running"
            if self._xapp_pids():
                return "[ACK] Already running"
            log.info("Starting %s", self.xapp_bin)
            self._process = subprocess.Popen(
                [self.xapp_bin],
                cwd=self.cwd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            log.info("Started %s (PID %s)", XAPP_COMM, self._process.pid)
            return "[ACK] Started"

    def status(self) -> str:
        return "[ACK] running" if self.is_running() else "[ACK] stopped"


def parse_command(raw: str) -> str:
    """Return command verb (START/STOP/STATUS/EXIT)."""
    msg = (raw or "").strip().upper()
    for verb in ("START", "STOP", "STATUS", "EXIT"):
        if msg.startswith(verb):
            return verb
    return ""


class MonitorTCPHandler(socketserver.BaseRequestHandler):
    manager: XappProcessManager

    def handle(self) -> None:
        peer = self.client_address
        log.info("Connection from %s", peer)
        while True:
            try:
                chunk = self.request.recv(1024)
                if not chunk:
                    break
                message = chunk.decode(errors="replace").strip()
                if not message:
                    break
                log.info("Received command: %s", message)
                verb = parse_command(message)
                if verb == "START":
                    reply = self.manager.start()
                elif verb == "STOP":
                    reply = self.manager.stop()
                elif verb == "STATUS":
                    reply = self.manager.status()
                elif verb == "EXIT":
                    reply = self.manager.stop()
                else:
                    reply = "[ERR] Unknown command"
                self.request.sendall(f"{reply}\n".encode())
            except (ConnectionResetError, BrokenPipeError):
                break
        log.info("Connection from %s closed", peer)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="pyoranris xApp monitor server (legacy xapp_kpm_rc launcher on :5005)"
    )
    p.add_argument("--host", default="127.0.0.1", help="Listen address (default: 127.0.0.1)")
    p.add_argument("--port", type=int, default=5005, help="Listen port (default: 5005)")
    p.add_argument(
        "--xapp-bin",
        required=True,
        help="Path to xapp_kpm_rc binary",
    )
    p.add_argument(
        "--cwd",
        default="",
        help="Working directory when launching xapp_kpm_rc",
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Debug logging",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )
    manager = XappProcessManager(args.xapp_bin, cwd=args.cwd or None)
    MonitorTCPHandler.manager = manager

    with ThreadedTCPServer((args.host, args.port), MonitorTCPHandler) as server:
        log.info("Monitor server listening on %s:%s", args.host, args.port)
        log.info("Commands: START, STOP, STATUS, EXIT (xapp only; server stays up)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            log.info("Shutting down monitor server")
            manager.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
