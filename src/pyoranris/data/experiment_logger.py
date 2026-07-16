"""CSV-only experiment logging (one or more files per run under ``data/``)."""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path

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

# KPM MAC stream (extends demo schema with SINR / ran_ue / RIS)
CSV_HEADER_KPM = [
    "timestamp",
    "t_rel_s",
    "ran_ue_id",
    "RSRP",
    "SINR",
    "RIS_index",
    "RIS_Angle",
    "update_latency",
]

# SRS CIR/CFR meta (no full IQ dump)
CSV_HEADER_SRS = [
    "timestamp",
    "t_rel_s",
    "rnti",
    "ue_id",
    "sfn",
    "slot",
    "peak_bin",
    "peak_mag",
    "n_cfr",
    "RIS_index",
    "RIS_Angle",
]


def ensure_dirs(paths) -> None:
    for path in paths:
        os.makedirs(path, exist_ok=True)


class ExperimentLogger:
    """One CSV file per run under ``root_dir`` (default ``data/``)."""

    def __init__(
        self,
        root_dir: str = "data",
        *,
        schema: str = "demo",
        name_suffix: str = "",
        stamp: str | None = None,
    ):
        self.root = Path(root_dir)
        self.schema = schema
        if stamp is None:
            stamp = datetime.now(timezone.utc).strftime("%a_%b_%d_%H_%M_%S_%f_%Z_%Y")
        self.stamp = stamp
        ensure_dirs([self.root])
        self.run_dir = self.root
        suffix = f"_{name_suffix}" if name_suffix else ""
        self.csv_path = self.root / f"run_{stamp}{suffix}.csv"
        self._fh = open(self.csv_path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fh)
        if schema == "kpm":
            header = CSV_HEADER_KPM
        elif schema == "srs":
            header = CSV_HEADER_SRS
        else:
            header = CSV_HEADER
        self._writer.writerow(header)
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

    def log_kpm_row(
        self,
        timestamp,
        t_rel_s,
        ran_ue_id,
        rsrp,
        sinr,
        update_latency=0.0,
        ris_index=None,
        ris_angle=None,
    ) -> None:
        self._writer.writerow(
            [
                timestamp,
                t_rel_s,
                ran_ue_id,
                rsrp,
                sinr,
                ris_index,
                ris_angle,
                update_latency,
            ]
        )
        self._fh.flush()

    def log_srs_row(
        self,
        timestamp,
        t_rel_s,
        rnti,
        ue_id,
        sfn,
        slot,
        peak_bin,
        peak_mag,
        n_cfr,
        ris_index=None,
        ris_angle=None,
    ) -> None:
        self._writer.writerow(
            [
                timestamp,
                t_rel_s,
                rnti,
                ue_id,
                sfn,
                slot,
                peak_bin,
                peak_mag,
                n_cfr,
                ris_index,
                ris_angle,
            ]
        )
        self._fh.flush()

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.close()
