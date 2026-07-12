"""Sivers UE EVK beam control via RPyC (optional dependency)."""

from __future__ import annotations

import logging
import socket

log = logging.getLogger(__name__)


class UEEvkDevice:
    def __init__(
        self,
        host: str,
        rx_port: int = 18814,
        tx_port: int = 18815,
        enabled: bool = False,
        initialize: bool = False,
        default_beam: int = 10,
    ):
        self.enabled = enabled
        self.host = host
        self.rx_port = rx_port
        self.tx_port = tx_port
        self.rx_conn = None
        self.tx_conn = None
        self.last_rx_index = default_beam
        if enabled:
            self._connect(initialize=initialize, default_beam=default_beam)

    def _connect(self, *, initialize: bool, default_beam: int) -> None:
        try:
            import rpyc
        except ImportError as exc:
            raise RuntimeError(
                "rpyc is required for UE EVK control. pip install rpyc"
            ) from exc
        self.rx_conn = rpyc.connect(
            self.host,
            self.rx_port,
            config={"sync_request_timeout": 1, "compression": True, "keepalive": 1},
        )
        self.rx_conn._channel.stream.sock.setsockopt(
            socket.IPPROTO_TCP, socket.TCP_NODELAY, 1
        )
        self.tx_conn = rpyc.connect(self.host, self.tx_port)
        self.tx_conn._channel.stream.sock.setsockopt(
            socket.IPPROTO_TCP, socket.TCP_NODELAY, 1
        )
        if initialize:
            self.set_beam(default_beam)
        log.info("UE EVK connected at %s", self.host)

    def get_beam(self) -> int:
        if not self.enabled or self.rx_conn is None:
            return int(self.last_rx_index)
        self.last_rx_index = int(self.rx_conn.root.exposed_execute_get_beam())
        return self.last_rx_index

    def set_beam(self, index: int) -> int:
        if not self.enabled or self.rx_conn is None or self.tx_conn is None:
            self.last_rx_index = int(index)
            return self.last_rx_index
        self.last_rx_index = int(self.rx_conn.root.exposed_execute_beam(f"set{index}"))
        self.tx_conn.root.exposed_execute_beam(f"set{index}")
        return self.last_rx_index

    def close(self) -> None:
        for conn in (self.rx_conn, self.tx_conn):
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
        self.rx_conn = None
        self.tx_conn = None
