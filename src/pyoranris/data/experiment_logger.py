"""Experiment folder + CSV logging (schema frozen from MILCOM_demo)."""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# Stable CSV header from the Jul 2026 working demo
CSV_HEADER = [
    "timestamp",
    "update_latency",
    "RSRP",
    "RIS_index",
    "RX_index",
    "RIS_Angle",
    "RX_Angle",
]


def ensure_dirs(paths) -> None:
    for path in paths:
        os.makedirs(path, exist_ok=True)


class ExperimentLogger:
    """Creates Demo/UE_Mobility/Experiment_at_*/data_log.csv style runs."""

    def __init__(self, root_dir: str = "data", mobility_subdir: str = "UE_Mobility"):
        self.root = Path(root_dir)
        self.mobility_dir = self.root / mobility_subdir
        stamp = datetime.now(timezone.utc).strftime("%a_%b_%d_%H_%M_%S_%f_%Z_%Y")
        self.run_dir = self.mobility_dir / f"Experiment_at_{stamp}"
        self.raw_dir = self.run_dir / "Raw_data"
        ensure_dirs(
            [
                self.run_dir,
                self.raw_dir,
                self.raw_dir / "Position_xyz",
                self.raw_dir / "RIS_rsrp",
                self.raw_dir / "RIS_Throughput",
                self.raw_dir / "latencies",
                self.raw_dir / "RIS_RX_index",
                self.raw_dir / "time_now",
            ]
        )
        self.csv_path = self.run_dir / "data_log.csv"
        self._fh = open(self.csv_path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fh)
        self._writer.writerow(CSV_HEADER)
        self._fh.flush()

    def log_row(
        self,
        timestamp,
        update_latency,
        rsrp,
        ris_index,
        rx_index,
        ris_angle,
        rx_angle,
    ) -> None:
        self._writer.writerow(
            [timestamp, update_latency, rsrp, ris_index, rx_index, ris_angle, rx_angle]
        )
        self._fh.flush()

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.close()


def save_kpi_data(root_dir, run_term, instance, data_dict):
    """Legacy .npy dump helper retained for compatibility."""
    ue_mob_dir = os.path.join(
        root_dir,
        f'Experiment_at_{datetime.now(timezone.utc).strftime("%a_%b_%d_%H_%M_%S_%f_%Z_%Y")}',
    )
    raw_dir = os.path.join(ue_mob_dir, "Raw_data")
    folders = {
        "rsrp": os.path.join(raw_dir, "RIS_rsrp"),
        "throughput": os.path.join(raw_dir, "RIS_Throughput"),
        "pos": os.path.join(raw_dir, "Position_xyz"),
        "lat": os.path.join(raw_dir, "latencies"),
        "index": os.path.join(raw_dir, "RIS_RX_index"),
    }
    ensure_dirs(list(folders.values()))
    pc_utc_time = datetime.now(timezone.utc).strftime("%a_%b_%d_%H_%M_%S_%f_%Z_%Y")
    paths = {
        "rsrp": os.path.join(folders["rsrp"], f"rsrp_run_{run_term}_{instance}_{pc_utc_time}.npy"),
        "latency": os.path.join(folders["lat"], f"time_run_{run_term}_{instance}_{pc_utc_time}.npy"),
        "throughput": os.path.join(
            folders["throughput"], f"dl_ul_throughput_run_{run_term}_{instance}_{pc_utc_time}.npy"
        ),
        "index": os.path.join(
            folders["index"], f"ris_rx_index_run_{run_term}_{instance}_{pc_utc_time}.npy"
        ),
    }
    np.save(paths["rsrp"], data_dict["RSRP"])
    np.save(
        paths["latency"],
        np.array(
            (
                data_dict.get("latency", 0),
                data_dict.get("update_latency", 0),
                data_dict.get("time_now", 0),
            )
        ),
    )
    np.save(paths["throughput"], np.array((data_dict["DLTH"], data_dict["ULTH"])))
    np.save(
        paths["index"],
        np.array((int(data_dict["RIS_index"]), int(data_dict["RX_index"]))),
    )
    return paths
