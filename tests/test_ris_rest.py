"""Tests for RIS REST beam apply client."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from pyoranris.config import load_config
from pyoranris.controllers.controller import Controller
from pyoranris.devices.ris_rest import RISRestClient


class _Handler(BaseHTTPRequestHandler):
    last_body = None
    last_path = None

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        _Handler.last_body = self.rfile.read(length)
        _Handler.last_path = self.path
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, format, *args):  # noqa: A003
        return


def test_ris_rest_apply_posts_json():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    th = threading.Thread(target=server.handle_request, daemon=True)
    th.start()

    client = RISRestClient(f"http://127.0.0.1:{port}/api/beam/apply", timeout=2.0)
    assert client.set_beam(7) == 7
    th.join(timeout=2)
    server.server_close()

    assert _Handler.last_path == "/api/beam/apply"
    assert json.loads(_Handler.last_body.decode()) == {"index": 7}
    assert "OK" in client.last_status


def test_kpm_config_enables_ris_rest():
    cfg = load_config("configs/kpm_mac_rsrp.yaml")
    assert cfg.features.ris_rest is True
    assert "beam/apply" in cfg.network.ris_rest_url


def test_controller_set_ris_beam_rest(monkeypatch):
    cfg = load_config("configs/kpm_mac_rsrp.yaml")
    cfg.features.record_mobility = False
    cfg.features.auto_connect_mac_rsrp = False
    ctrl = Controller(cfg)
    try:
        assert ctrl.ris_rest is not None

        def fake_set(index: int) -> int:
            ctrl.ris_rest.last_status = "OK HTTP 200"
            ctrl.ris_rest.last_beam = index
            return index

        monkeypatch.setattr(ctrl.ris_rest, "set_beam", fake_set)
        assert ctrl.set_ris_beam(3) == 3
        assert ctrl.get_snapshot().current_ris_beam == 3
    finally:
        ctrl.stop_background_workers()
