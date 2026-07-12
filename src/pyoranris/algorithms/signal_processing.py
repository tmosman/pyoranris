"""Lightweight signal helpers used by mobility logic."""

from __future__ import annotations

import numpy as np


def smooth_data(values, window: int = 5) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return arr
    window = max(1, min(window, arr.size))
    kernel = np.ones(window) / window
    return np.convolve(arr, kernel, mode="same")


def is_descending(values, min_len: int = 3) -> bool:
    arr = np.asarray(values, dtype=float)
    if arr.size < min_len:
        return False
    return bool(np.all(np.diff(arr[-min_len:]) < 0))
