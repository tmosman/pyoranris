"""Hardware device adapters."""

from __future__ import annotations

__all__ = ["MarvelmindHedge", "RISDevice", "UEEvkDevice", "RobotDevice", "PositionDevice"]


def __getattr__(name: str):
    if name == "MarvelmindHedge":
        from pyoranris.devices.marvelmind import MarvelmindHedge

        return MarvelmindHedge
    if name == "RISDevice":
        from pyoranris.devices.ris import RISDevice

        return RISDevice
    if name == "UEEvkDevice":
        from pyoranris.devices.ue_evk import UEEvkDevice

        return UEEvkDevice
    if name == "RobotDevice":
        from pyoranris.devices.robot import RobotDevice

        return RobotDevice
    if name == "PositionDevice":
        from pyoranris.devices.marvelmind_device import PositionDevice

        return PositionDevice
    raise AttributeError(name)
