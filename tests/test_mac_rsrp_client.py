"""Unit tests for KPM MAC RSRP text protocol + client."""

from __future__ import annotations

import socket
import threading
import time

from pyoranris.config import load_config
from pyoranris.controllers.controller import Controller
from pyoranris.net.mac_rsrp_client import MacRsrpTcpClient, parse_data_line


def test_parse_data_line_4col():
    row = parse_data_line("1000000 3 -72.5 12.0")
    assert row == (1000000, 3, -72.5, 12.0)


def test_parse_data_line_3col_legacy():
    row = parse_data_line("1000000 3 -72.5")
    assert row[0] == 1000000
    assert row[2] == -72.5
    assert row[3] != row[3]  # NaN


def test_parse_sentinel_mapped_by_client_path():
    from pyoranris.net.mac_rsrp_client import _map_sentinel

    assert _map_sentinel(-1000.0) != _map_sentinel(-1000.0)  # NaN
    assert _map_sentinel(-70.0) == -70.0


def _serve_lines(port: int, lines: list[str], ready: threading.Event, stop: threading.Event):
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(1)
    ready.set()
    srv.settimeout(2.0)
    try:
        conn, _ = srv.accept()
        with conn:
            for line in lines:
                conn.sendall((line + "\n").encode())
                time.sleep(0.05)
            while not stop.is_set():
                time.sleep(0.05)
    except Exception:
        pass
    finally:
        srv.close()


def test_mac_client_receives_samples():
    port = 18081
    ready = threading.Event()
    stop = threading.Event()
    lines = [
        "1000000 1 -70.0 10.0",
        "1100000 1 -71.0 11.0",
        "1200000 1 -72.0 12.0",
    ]
    th = threading.Thread(target=_serve_lines, args=(port, lines, ready, stop), daemon=True)
    th.start()
    assert ready.wait(2)
    client = MacRsrpTcpClient("127.0.0.1", port)
    client.start()
    try:
        deadline = time.time() + 3
        got = []
        while time.time() < deadline and len(got) < 3:
            try:
                got.append(client.data_queue.get(timeout=0.5))
            except Exception:
                pass
        assert len(got) >= 2
        assert got[0].rsrp == -70.0
        assert got[0].sinr == 10.0
        assert got[1].t_rel_s > 0
    finally:
        stop.set()
        client.stop()


def test_kpm_config_loads():
    cfg = load_config("configs/kpm_mac_rsrp.yaml")
    assert cfg.profile == "kpm_mac_rsrp"
    assert cfg.features.mac_rsrp_tcp is True
    assert cfg.features.xapp_server is False
    assert cfg.network.xapp_port == 8081


def test_controller_kpm_mode_wires_client():
    cfg = load_config("configs/kpm_mac_rsrp.yaml")
    cfg.features.record_mobility = False
    cfg.features.auto_connect_mac_rsrp = False
    ctrl = Controller(cfg)
    try:
        assert ctrl.mac_client is not None
        assert ctrl.xapp is None  # must not bind :8081 as server
        assert ctrl.flexric is not None
    finally:
        ctrl.stop_background_workers()
