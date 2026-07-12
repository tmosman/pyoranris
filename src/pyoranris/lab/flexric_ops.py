"""Optional lab process helpers (flexric KPM xApp start/stop via shell script)."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


def _expand(path: str) -> str:
    return os.path.expanduser(os.path.expandvars(path))


class FlexricKpmLauncher:
    """Thin wrapper around oai-flexric.sh start/stop/status xapp-kpm."""

    def __init__(
        self,
        script: str = "~/Program_scripts/flexric_scripts/oai-flexric.sh",
        report_period_ms: int = 100,
        duration: int = -1,
    ):
        self.script = _expand(script)
        self.report_period_ms = report_period_ms
        self.duration = duration

    def available(self) -> bool:
        return Path(self.script).is_file() and os.access(self.script, os.X_OK)

    def _env(self) -> dict:
        env = os.environ.copy()
        env["KPM_REPORT_PERIOD_MS"] = str(self.report_period_ms)
        env["XAPP_DURATION"] = str(self.duration)
        return env

    def start(self) -> str:
        if not self.available():
            return f"Script not found/executable: {self.script}"
        cmd = [self.script, "start", "xapp-kpm"]
        try:
            proc = subprocess.run(
                cmd, env=self._env(), capture_output=True, text=True, timeout=60
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            if proc.returncode != 0:
                return f"start failed ({proc.returncode}): {out[-400:]}"
            return out.strip() or "xapp-kpm start issued"
        except Exception as exc:
            log.exception("flexric start failed")
            return f"start error: {exc}"

    def stop(self) -> str:
        if not self.available():
            return f"Script not found/executable: {self.script}"
        try:
            proc = subprocess.run(
                [self.script, "stop", "xapp-kpm"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            if proc.returncode != 0:
                return f"stop failed ({proc.returncode}): {out[-400:]}"
            return out.strip() or "xapp-kpm stop issued"
        except Exception as exc:
            return f"stop error: {exc}"

    def status(self) -> str:
        if not self.available():
            return f"Script not found/executable: {self.script}"
        try:
            proc = subprocess.run(
                [self.script, "status", "xapp-kpm"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return ((proc.stdout or "") + (proc.stderr or "")).strip() or "(empty)"
        except Exception as exc:
            return f"status error: {exc}"
