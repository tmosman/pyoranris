"""Beam index neighborhood search (cleaned API + legacy-compatible helpers)."""

from __future__ import annotations

import numpy as np


class BeamIndexOptimizer:
    """Return nearby RIS/RX beam indices around the current pointing."""

    def __init__(
        self,
        max_ris_index: int = 182,
        max_rx_index: int = 10,
        current_ris_index: int = 0,
        current_rx_index: int = 0,
        num_index_interval: int = 1,
    ):
        self.max_ris_index = int(max_ris_index)
        self.max_rx_index = int(max_rx_index)
        self.current_ris_index = int(current_ris_index)
        self.current_rx_index = int(current_rx_index)
        self.num_index_interval = int(num_index_interval)

    def get_rx_beam_index_range(self) -> np.ndarray:
        low = max(0, self.current_rx_index - self.num_index_interval)
        high = min(self.max_rx_index - 1, self.current_rx_index + self.num_index_interval)
        return np.arange(low, high + 1)

    def get_ris_beam_index_range(self) -> np.ndarray:
        low = max(0, self.current_ris_index - self.num_index_interval)
        high = min(self.max_ris_index - 1, self.current_ris_index + self.num_index_interval)
        return np.arange(low, high + 1)


class LegacyBeamIndexOptimizer:
    """Port of the original classes_file.BeamIndexOptimizer (asymmetric probe set)."""

    def __init__(
        self,
        max_ris_index,
        max_rx_index,
        current_ris_index,
        current_rx_index,
        num_index_interval,
    ):
        self.max_ris_index = max_ris_index
        self.max_rx_index = max_rx_index
        self.current_ris_index = current_ris_index
        self.current_rx_index = current_rx_index
        self.num_index_interval = num_index_interval

    def get_ris_beam_index_range(self) -> np.ndarray:
        cur = self.current_ris_index
        step = self.num_index_interval
        if (cur - step > 0 and cur + step < self.max_ris_index) or (cur - 2 * step > 0):
            return np.array([cur, cur - 2 * step, cur + 2 * step])
        if (cur - step < 0) or (cur - 2 * step < 0):
            return np.array([cur, cur + step, cur + step + 1])
        if cur + step >= self.max_ris_index:
            return np.array([cur, cur - step])
        return np.array([cur])

    def get_rx_beam_index_range(self) -> np.ndarray:
        cur = self.current_rx_index
        if 0 < cur < self.max_rx_index:
            return np.array([cur - 1, cur, cur + 1])
        if cur == 10:
            return np.array([cur - 2, cur - 1, cur])
        if cur == 0:
            return np.array([cur, cur + 1])
        return np.array([cur, cur - 1])


class BeamSearch:
    """Sweep candidate beams using a measurement callback."""

    def __init__(self, optimizer: BeamIndexOptimizer):
        self.optimizer = optimizer

    def sweep(self, get_rsrp_fn, update_state_fn=None):
        candidates = self.optimizer.get_ris_beam_index_range()
        results: dict[int, float] = {}
        for beam in candidates:
            rsrp = float(get_rsrp_fn(beam))
            results[int(beam)] = rsrp
            if update_state_fn:
                update_state_fn(beam, rsrp)
        best = max(results.items(), key=lambda kv: kv[1])[0]
        return int(best), results
