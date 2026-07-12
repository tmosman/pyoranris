"""Hardware device adapters."""

from __future__ import annotations

__all__ = ["MarvelmindHedge"]


def __getattr__(name: str):
    if name == "MarvelmindHedge":
        from pyoranris.devices.marvelmind import MarvelmindHedge

        return MarvelmindHedge
    raise AttributeError(name)
