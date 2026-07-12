"""Tests for RIS REST beam apply client."""

from __future__ import annotations

import json
import threading
import time
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
    cfg.features.auto_apply_ris_on_start = False
    ctrl = Controller(cfg)
    try:
        assert ctrl.ris_rest is not None

        def fake_set(index: int) -> int:
            ctrl.ris_rest.last_status = "OK HTTP 200"
            ctrl.ris_rest.last_beam = index
            return index

        monkeypatch.setattr(ctrl.ris_rest, "set_beam", fake_set)
        assert ctrl.set_ris_beam(3) == 3
        snap = ctrl.get_snapshot()
        assert snap.current_ris_beam == 3
        assert abs(snap.current_ris_angle - 20.0 - 3 * (60.0 - 20.0) / 21) < 1e-6
    finally:
        ctrl.stop_background_workers()


def test_ris_index_to_angle_endpoints():
    from pyoranris.algorithms.mobility import ris_index_to_angle

    assert ris_index_to_angle(0, max_index=21, angle_min=20, angle_max=60) == 20.0
    assert ris_index_to_angle(21, max_index=21, angle_min=20, angle_max=60) == 60.0


def test_mac_sample_tracks_ris_beam(monkeypatch):
    from pyoranris.net.mac_rsrp_client import MacKpiSample

    cfg = load_config("configs/kpm_mac_rsrp.yaml")
    cfg.features.record_mobility = False
    cfg.features.auto_connect_mac_rsrp = False
    cfg.features.auto_apply_ris_on_start = False
    ctrl = Controller(cfg)
    try:
        monkeypatch.setattr(ctrl.ris_rest, "set_beam", lambda index: index)
        ctrl.set_ris_beam(10)
        ctrl._append_mac_sample(
            MacKpiSample(collect_us=1000, ran_ue=1, rsrp=-70.0, sinr=12.0, t_rel_s=1.0)
        )
        snap = ctrl.get_snapshot()
        assert snap.ris_index_series[-1] == 10.0
        assert abs(snap.ris_angle_series[-1] - snap.current_ris_angle) < 1e-9
    finally:
        ctrl.stop_background_workers()


def test_bootstrap_default_ris_on_start(monkeypatch):
    cfg = load_config("configs/kpm_mac_rsrp.yaml")
    cfg.features.record_mobility = False
    cfg.features.auto_connect_mac_rsrp = False
    cfg.features.auto_apply_ris_on_start = True
    cfg.beams.default_ris_index = 5
    applied: list[int] = []

    # Patch before Controller so background bootstrap uses the fake
    from pyoranris.devices.ris_rest import RISRestClient

    orig_init = RISRestClient.__init__

    def init_and_patch(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)

        def fake_set(index: int) -> int:
            applied.append(index)
            self.last_status = "OK HTTP 200"
            self.last_beam = index
            return index

        self.set_beam = fake_set  # type: ignore[method-assign]

    monkeypatch.setattr(RISRestClient, "__init__", init_and_patch)
    ctrl = Controller(cfg)
    try:
        # Wait briefly for daemon bootstrap thread
        for _ in range(50):
            if applied:
                break
            time.sleep(0.02)
        assert applied == [5]
        snap = ctrl.get_snapshot()
        assert snap.current_ris_beam == 5
        assert snap.current_ris_angle == snap.current_ris_angle  # not NaN
    finally:
        ctrl.stop_background_workers()
