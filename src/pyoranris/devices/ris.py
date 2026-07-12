"""RIS beam steering adapter."""

from __future__ import annotations

import logging

from pyoranris.net.lab_tcp import LabTCPClient

log = logging.getLogger(__name__)


class RISDevice:
    def __init__(self, host: str, port: int, enabled: bool = True):
        self.enabled = enabled
        self._client = LabTCPClient(host, port) if enabled else None
        self.last_beam: int | None = None

    def get_beam(self) -> int:
        if not self.enabled or self._client is None:
            return int(self.last_beam or 0)
        raw = self._client.get_ris_beam("GET")
        try:
            self.last_beam = int(raw)
        except (TypeError, ValueError):
            self.last_beam = 0
        return int(self.last_beam)

    def set_beam(self, index: int, cmd: str = "RIS") -> int:
        if not self.enabled or self._client is None:
            self.last_beam = int(index)
            return self.last_beam
        raw = self._client.send_ris_ACK(cmd, int(index))
        try:
            self.last_beam = int(raw)
        except (TypeError, ValueError):
            self.last_beam = int(index)
        return int(self.last_beam)
