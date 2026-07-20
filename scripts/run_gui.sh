#!/usr/bin/env bash
# Launch pyoranris GUI with DISPLAY + xhost setup for fresh SSH/sudo shells.
#
# Usage:
#   ./scripts/run_gui.sh -c configs/indoor_mobility.yaml
#
# Config alternative (no script): lab_default gui.auto_detect_display + auto_xhost
# Env override: export PYORANRIS_DISPLAY=:0.0

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -z "${DISPLAY:-}" ]]; then
  if command -v who >/dev/null 2>&1; then
    DETECTED="$(who 2>/dev/null | grep -oE ':[0-9]+(\.[0-9]+)?' | head -1 || true)"
    if [[ -n "$DETECTED" && "$DETECTED" != *.* ]]; then
      DETECTED="${DETECTED}.0"
    fi
  fi
  if [[ -z "${DETECTED:-}" && -S /tmp/.X11-unix/X0 ]]; then
    DETECTED=":0.0"
  fi
  export DISPLAY="${PYORANRIS_DISPLAY:-${DETECTED:-:0.0}}"
  echo "DISPLAY=$DISPLAY"
fi

if command -v xhost >/dev/null 2>&1; then
  XUSER="${PYORANRIS_XHOST_USER:-${SUDO_USER:-${USER:-root}}}"
  if [[ "$(id -u)" -eq 0 && -z "${SUDO_USER:-}" ]]; then
    XUSER="${PYORANRIS_XHOST_USER:-root}"
  fi
  if xhost "+si:localuser:${XUSER}" 2>/dev/null; then
    echo "xhost +si:localuser:${XUSER} OK"
  else
    echo "WARN: xhost failed — run once from your desktop (non-sudo) terminal:" >&2
    echo "  xhost +si:localuser:${XUSER}" >&2
  fi
fi

exec pyoranris run "$@"
