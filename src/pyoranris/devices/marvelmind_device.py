"""Marvelmind indoor positioning adapter (optional pyserial)."""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)


class PositionDevice:
    def __init__(self, tty: str = "/dev/ttyACM0", baud: int = 115200, enabled: bool = False):
        self.enabled = enabled
        self.hedge = None
        self.last_xyz = np.array([0.0, 0.0, 0.0])
        if enabled:
            from pyoranris.devices.marvelmind import MarvelmindHedge

            self.hedge = MarvelmindHedge(tty=tty, baud=baud, adr=None, debug=False)
            self.hedge.start()
            log.info("Marvelmind started on %s", tty)

    def read_xyz(self) -> np.ndarray:
        if not self.enabled or self.hedge is None:
            return self.last_xyz.copy()
        self.hedge.dataEvent.wait(1e-2)
        self.hedge.dataEvent.clear()
        if self.hedge.positionUpdated:
            pos, _ = self.hedge.print_position_1()
            self.last_xyz = np.array([pos[1], pos[2], pos[3]], dtype=float)
        return self.last_xyz.copy()

    def stop(self) -> None:
        if self.hedge is not None:
            try:
                self.hedge.stop()
            except Exception:
                pass
