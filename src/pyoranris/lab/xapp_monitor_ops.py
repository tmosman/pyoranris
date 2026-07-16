"""Launch and probe the legacy xApp monitor server (:5005)."""

from __future__ import annotations

import logging
import os
import socket
import subprocess
import sys
from pathlib import Path

from pyoranris.net.lab_tcp import LabTCPClient

log = logging.getLogger(__name__)


def _expand(path: str) -> str:
    return os.path.expanduser(os.path.expandvars(path))


class XappMonitorLauncher:
    """Spawn ``pyoranris.lab.xapp_monitor_server`` and probe it via TCP."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5005,
        xapp_bin: str = "",
        cwd: str = "",
    ):
        self.host = host
        self.port = int(port)
        self.xapp_bin = _expand(xapp_bin)
        self.cwd = _expand(cwd) if cwd else ""
        self._proc: subprocess.Popen | None = None

    def _client(self) -> LabTCPClient:
        return LabTCPClient(self.host, self.port, timeout=2.0)

    def probe(self) -> bool:
        """Return True if monitor server accepts STATUS."""
        try:
            with socket.create_connection((self.host, self.port), timeout=0.5):
                pass
        except OSError:
            return False
        try:
            reply = self._client().send_oai_ue_ACK("STATUS", 0)
            return bool(reply)
        except Exception:
            return False

    def query_status(self) -> str:
        if not self.probe():
            return "monitor server not reachable"
        return self._client().send_oai_ue_ACK("STATUS", 0)

    def ensure_running(self) -> str:
        if self.probe():
            return f"monitor server already listening on {self.host}:{self.port}"
        if not self.xapp_bin:
            return "xapp_kpm_rc path not configured (lab_ops.xapp_kpm_rc_bin)"
        if not Path(self.xapp_bin).is_file():
            return f"xApp binary not found: {self.xapp_bin}"
        return self.start_server()

    def start_server(self) -> str:
        if self._proc is not None and self._proc.poll() is None:
            return f"monitor server subprocess running (pid={self._proc.pid})"
        cmd = [
            sys.executable,
            "-m",
            "pyoranris.lab.xapp_monitor_server",
            "--host",
            self.host,
            "--port",
            str(self.port),
            "--xapp-bin",
            self.xapp_bin,
        ]
        if self.cwd:
            cmd.extend(["--cwd", self.cwd])
        try:
            self._proc = subprocess.Popen(
                cmd,
                cwd=self.cwd or None,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            log.info("Started xApp monitor server pid=%s", self._proc.pid)
            return f"monitor server started on {self.host}:{self.port}"
        except Exception as exc:
            log.exception("Failed to start monitor server")
            return f"monitor server start failed: {exc}"

    def stop_server(self) -> None:
        if self._proc is None:
            return
        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None
