"""Auto-set DISPLAY (and optional xhost) before DearPyGui/GLFW starts."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

_WHO_DISPLAY_RE = re.compile(r"(:\d+(?:\.\d+)?)")


def detect_display() -> str | None:
    """Guess X11 DISPLAY when unset (who, then /tmp/.X11-unix)."""
    existing = os.environ.get("DISPLAY", "").strip()
    if existing:
        return existing

    if shutil.which("who"):
        try:
            out = subprocess.check_output(["who"], text=True, timeout=2, stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                match = _WHO_DISPLAY_RE.search(line)
                if match:
                    disp = match.group(1)
                    if "." not in disp:
                        disp = f"{disp}.0"
                    return disp
        except (subprocess.SubprocessError, OSError):
            pass

    x_dir = Path("/tmp/.X11-unix")
    if x_dir.is_dir():
        sockets = sorted(p.name for p in x_dir.glob("X*") if p.name[1:].isdigit())
        if sockets:
            n = sockets[-1][1:]
            return f":{n}.0"

    return None


def _xhost_target_user(cfg_user: str) -> str:
    if cfg_user.strip():
        return cfg_user.strip()
    if os.environ.get("SUDO_USER"):
        return os.environ["SUDO_USER"]
    if os.geteuid() == 0:
        return "root"
    return os.environ.get("USER") or os.environ.get("LOGNAME") or "root"


def try_xhost_local_user(cfg_user: str = "") -> bool:
    """Run ``xhost +si:localuser:<user>`` (best-effort; may need a GUI session)."""
    if not shutil.which("xhost"):
        log.warning("xhost not found; skip X11 access grant")
        return False
    user = _xhost_target_user(cfg_user)
    spec = f"+si:localuser:{user}"
    try:
        proc = subprocess.run(
            ["xhost", spec],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        log.warning("xhost %s failed: %s", spec, exc)
        return False
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        log.warning(
            "xhost %s failed (exit %s): %s — run from your desktop session if using sudo",
            spec,
            proc.returncode,
            err or "no output",
        )
        return False
    log.info("xhost %s OK (localuser=%s)", spec, user)
    return True


def ensure_x11_for_gui(
    *,
    display: str = "",
    auto_detect: bool = True,
    auto_xhost: bool = False,
    xhost_user: str = "",
) -> str | None:
    """Set os.environ['DISPLAY'] before importing DearPyGui. Returns DISPLAY or None."""
    disp = (display or os.environ.get("DISPLAY", "")).strip()
    if not disp and auto_detect:
        disp = detect_display() or ""
    if disp:
        os.environ["DISPLAY"] = disp
        log.info("DISPLAY=%s", disp)
    else:
        log.warning(
            "DISPLAY is not set and auto-detect failed — DearPyGui needs X11 or use --headless"
        )
        return None

    if auto_xhost:
        try_xhost_local_user(xhost_user)

    return disp
