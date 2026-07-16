"""Tests for legacy xApp monitor server command parsing and process manager."""

from __future__ import annotations

from pyoranris.lab.xapp_monitor_server import XappProcessManager, parse_command


def test_parse_command():
    assert parse_command("START0") == "START"
    assert parse_command("stop") == "STOP"
    assert parse_command("STATUS") == "STATUS"
    assert parse_command("EXIT1") == "EXIT"
    assert parse_command("FOO") == ""


def test_status_when_not_running(tmp_path):
    missing = tmp_path / "no_such_xapp"
    mgr = XappProcessManager(str(missing))
    assert mgr.status() == "[ACK] stopped"


def test_start_missing_binary(tmp_path):
    missing = tmp_path / "no_such_xapp"
    mgr = XappProcessManager(str(missing))
    assert "[ERR]" in mgr.start()
