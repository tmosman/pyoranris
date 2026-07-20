"""Tests for X11 DISPLAY auto-detection."""

from __future__ import annotations

import os
from unittest import mock

from pyoranris.utils.x11_display import detect_display, ensure_x11_for_gui


def test_detect_display_from_who():
    with mock.patch.dict(os.environ, {}, clear=True):
        with mock.patch(
            "pyoranris.utils.x11_display.subprocess.check_output",
            return_value="tmosman  :0           2026-07-16 08:00 (:0)\n",
        ):
            assert detect_display() == ":0.0"


def test_detect_display_keeps_existing():
    with mock.patch.dict(os.environ, {"DISPLAY": ":1.0"}, clear=True):
        assert detect_display() == ":1.0"


def test_ensure_x11_sets_display(monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    with mock.patch(
        "pyoranris.utils.x11_display.detect_display",
        return_value=":0.0",
    ):
        with mock.patch("pyoranris.utils.x11_display.try_xhost_local_user") as xhost:
            result = ensure_x11_for_gui(auto_detect=True, auto_xhost=True)
            assert result == ":0.0"
            assert os.environ["DISPLAY"] == ":0.0"
            xhost.assert_called_once()
