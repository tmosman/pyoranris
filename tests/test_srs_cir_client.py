"""Unit tests for SRS CIR/CFR TCP client + config wiring."""

from __future__ import annotations

from pyoranris.config import load_config
from pyoranris.controllers.controller import Controller
from pyoranris.net.srs_cir_client import (
    SrsCirTcpClient,
    cfr_to_cir,
    parse_cfr_line,
    parse_meta_line,
)


def test_parse_meta_line():
    line = "META 1000 768 2 48609 1 1 1 1536 100 12.5"
    meta = parse_meta_line(line)
    assert meta is not None
    assert meta["sfn"] == 768
    assert meta["rnti"] == 48609
    assert meta["n_fft"] == 1536
    assert meta["peak_cfr_mag"] == 12.5


def test_parse_cfr_line_and_cir():
    # 4 bins of complex IQ
    iq = " ".join(f"{1.0} {0.0}" for _ in range(4))
    line = f"CFR 1000 768 2 48609 0 4 {iq}"
    row = parse_cfr_line(line)
    assert row is not None
    cfr, meta = row
    assert len(cfr) == 4
    assert meta["rnti"] == 48609
    cfr_mag, cir = cfr_to_cir(cfr, n_fft_hint=4)
    assert len(cfr_mag) == 4
    assert len(cir) == 4
    assert float(cfr_mag.max()) > 0


def test_srs_config_loads():
    cfg = load_config("configs/srs_cir.yaml")
    assert cfg.profile == "srs_cir"
    assert cfg.features.srs_cir_tcp is True
    assert cfg.features.mac_rsrp_tcp is False
    assert cfg.network.srs_port == 8082
    assert cfg.lab_ops.srs_max_bins == 1536
    assert cfg.features.auto_connect_srs_cir is True


def test_controller_srs_mode_wires_client():
    cfg = load_config("configs/srs_cir.yaml")
    cfg.features.auto_connect_srs_cir = False
    cfg.features.auto_apply_ris_on_start = False
    ctrl = Controller(cfg)
    try:
        assert ctrl.srs_client is not None
        assert ctrl.mac_client is None
        assert ctrl.xapp is None
        assert ctrl.flexric_srs is not None
        assert isinstance(ctrl.srs_client, SrsCirTcpClient)
    finally:
        ctrl.stop_background_workers()


def test_apply_srs_frame_updates_snapshot():
    import numpy as np

    from pyoranris.net.srs_cir_client import SrsFrame

    cfg = load_config("configs/srs_cir.yaml")
    cfg.features.auto_connect_srs_cir = False
    cfg.features.auto_apply_ris_on_start = False
    ctrl = Controller(cfg)
    try:
        frame = SrsFrame(
            collect_us=1,
            sfn=10,
            slot=1,
            rnti=99,
            ue_id=2,
            ant=0,
            n_fft=4,
            peak_cfr_bin=1,
            peak_cfr_mag=3.5,
            cfr_mag=np.array([1.0, 2.0, 1.5, 0.5]),
            cir_mag=np.array([0.1, 4.0, 0.2, 0.1]),
        )
        ctrl._apply_srs_frame(frame)
        snap = ctrl.get_snapshot()
        assert snap.srs_rnti == 99
        assert snap.srs_sfn == 10
        assert snap.cfr_mag == [1.0, 2.0, 1.5, 0.5]
        assert snap.cir_mag[1] == 4.0
    finally:
        ctrl.stop_background_workers()
