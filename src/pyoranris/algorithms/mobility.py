"""RSRP monitoring helpers for mobility re-optimization."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from pyoranris.algorithms.signal_processing import smooth_data as _smooth_fallback


def smooth_rsrp(y: Sequence[float]) -> np.ndarray:
    """Prefer Savitzky–Golay when scipy is available; else moving average."""
    arr = np.asarray(y, dtype=float)
    if arr.size == 0:
        return arr
    if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
        arr = np.nan_to_num(arr)
    try:
        from scipy.signal import savgol_filter
    except ImportError:
        return _smooth_fallback(arr, window=min(5, arr.size))

    polyorder = max(1, len(arr) - 1)
    value = min(len(arr) // 2, len(arr)) + 1
    window_length = value if value % 2 != 0 else value - 1
    window_length = max(3, window_length)
    if window_length > len(arr):
        window_length = len(arr) if len(arr) % 2 == 1 else max(1, len(arr) - 1)
    polyorder = min(polyorder, window_length - 1)
    if window_length < 3 or polyorder < 1:
        return _smooth_fallback(arr, window=min(5, arr.size))
    return savgol_filter(arr, window_length=window_length, polyorder=polyorder)


def is_descending(y: Sequence[float], threshold: float) -> tuple[bool, float]:
    arr = np.asarray(y, dtype=float)
    if arr.size < 2:
        return False, 0.0
    decreasing = int(np.sum(np.diff(arr) <= 0))
    span = abs(float(min(arr) - max(arr)))
    ok = (decreasing / len(arr) >= 0.6) and (span >= threshold)
    return ok, span


def index_to_angles(
    ris_index: int,
    rx_index: int,
    *,
    max_ris_index: int,
    rx_angles: Sequence[float],
) -> tuple[float, float]:
    if max_ris_index > 183:
        ris_angle = 20 + ((ris_index - 182) * 0.25)
    else:
        ris_angle = 20 + (ris_index * 0.25)
    rx_index = int(np.clip(rx_index, 0, len(rx_angles) - 1))
    return float(ris_angle), float(rx_angles[rx_index])


def ris_index_to_angle(
    ris_index: int,
    *,
    max_index: int = 21,
    angle_min: float = 20.0,
    angle_max: float = 60.0,
) -> float:
    """Map RIS beam index [0, max_index] → angle [angle_min, angle_max] degrees."""
    max_index = max(1, int(max_index))
    idx = int(np.clip(ris_index, 0, max_index))
    return float(angle_min + idx * (angle_max - angle_min) / max_index)


class RSRPMonitor:
    """Windowed RSRP drop detector (legacy monitor_rsrp_hybrid_v1)."""

    def __init__(self, window_len: int = 5):
        self.window_len = window_len
        self.check_begin: int | None = None
        self.buffer: list[float] = []
        self.counter = -1

    def reset(self) -> None:
        self.check_begin = None
        self.buffer = []
        self.counter = -1

    def push(self, rsrp: float) -> None:
        self.counter += 1
        self.buffer.append(float(rsrp))

    def evaluate(self, threshold: float = 1.0) -> tuple[bool, int]:
        if self.check_begin is None:
            window = self.buffer[0 : self.window_len]
        else:
            window = self.buffer[
                self.check_begin : self.check_begin + self.window_len + 1
            ]

        if len(window) < self.window_len:
            return False, 0

        self.check_begin = self.counter - self.window_len + 1
        smooth = smooth_rsrp(window)
        if is_descending(smooth, threshold)[0]:
            return True, -1
        if abs(max(window) - min(window)) >= threshold:
            return True, -1
        return False, -1
