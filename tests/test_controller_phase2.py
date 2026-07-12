from pyoranris.algorithms.mobility import RSRPMonitor, index_to_angles, is_descending
from pyoranris.config import load_config
from pyoranris.controllers.controller import Controller


def test_index_to_angles():
    ris, rx = index_to_angles(0, 5, max_ris_index=182, rx_angles=[-27, -21, -15, -9, -3, 0, 3, 9, 15, 21, 27])
    assert ris == 20.0
    assert rx == 0


def test_is_descending():
    ok, span = is_descending([-70, -71, -72, -73, -74], threshold=1.0)
    assert ok is True
    assert span >= 1.0


def test_rsrp_monitor_stable_then_drop():
    mon = RSRPMonitor(window_len=5)
    for v in [-70, -70, -70, -70, -70]:
        mon.push(v)
    dropped, _ = mon.evaluate(threshold=1.0)
    assert dropped is False
    for v in [-71, -72, -73, -74, -75]:
        mon.push(v)
    dropped, _ = mon.evaluate(threshold=1.0)
    assert dropped is True


def test_controller_offline_plot_loop():
    cfg = load_config("configs/offline_sim.yaml")
    cfg.features.record_mobility = False
    ctrl = Controller(cfg)
    ctrl.start_background_workers()
    try:
        ctrl.start_plotting()
        import time

        time.sleep(0.8)
        snap = ctrl.get_snapshot()
        assert snap.plotting is True
        assert len(snap.rsrp_series) > 0
    finally:
        ctrl.stop_background_workers()


def test_controller_set_beams_offline():
    cfg = load_config("configs/offline_sim.yaml")
    cfg.features.record_mobility = False
    ctrl = Controller(cfg)
    assert ctrl.set_ris_beam(42) == 42
    assert ctrl.set_ue_beam(3) == 3
    ctrl.stop_background_workers()
