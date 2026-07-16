"""Tests for combined KPM + SRS profile (Phase 3 Option A)."""

from __future__ import annotations

from pyoranris.config import load_config
from pyoranris.controllers.controller import Controller


def test_kpm_srs_config_loads():
    cfg = load_config("configs/kpm_srs.yaml")
    assert cfg.profile == "kpm_srs"
    assert cfg.features.mac_rsrp_tcp is True
    assert cfg.features.srs_cir_tcp is True
    assert cfg.network.xapp_port == 8081
    assert cfg.network.srs_port == 8082
    assert cfg.features.auto_connect_mac_rsrp is True
    assert cfg.features.auto_connect_srs_cir is True


def test_controller_combo_wires_both_clients():
    cfg = load_config("configs/kpm_srs.yaml")
    cfg.features.auto_connect_mac_rsrp = False
    cfg.features.auto_connect_srs_cir = False
    cfg.features.auto_apply_ris_on_start = False
    cfg.features.record_mobility = True
    ctrl = Controller(cfg)
    try:
        assert ctrl.mac_client is not None
        assert ctrl.srs_client is not None
        assert ctrl.flexric is not None
        assert ctrl.flexric_srs is not None
        assert ctrl.logger is not None
        assert ctrl.srs_logger is not None
        assert "_kpm" in ctrl.logger.csv_path.name or "kpm" in ctrl.logger.csv_path.name
        assert "srs" in ctrl.srs_logger.csv_path.name
        assert ctrl.xapp is None
    finally:
        ctrl.stop_background_workers()


def test_start_plotting_starts_both_threads():
    cfg = load_config("configs/kpm_srs.yaml")
    cfg.features.auto_connect_mac_rsrp = False
    cfg.features.auto_connect_srs_cir = False
    cfg.features.auto_apply_ris_on_start = False
    cfg.features.record_mobility = False
    ctrl = Controller(cfg)
    try:
        ctrl.start_plotting()
        assert ctrl._plot_thread is not None and ctrl._plot_thread.is_alive()
        assert ctrl._srs_plot_thread is not None and ctrl._srs_plot_thread.is_alive()
        snap = ctrl.get_snapshot()
        assert snap.plotting is True
        assert "KPM" in snap.status and "SRS" in snap.status
    finally:
        ctrl.stop_background_workers()
