from pyoranris.config import load_config


def test_offline_config_loads():
    cfg = load_config("configs/offline_sim.yaml")
    assert cfg.profile == "offline_sim"
    assert cfg.features.simulate_rsrp is True
    assert cfg.features.ris is False


def test_indoor_extends_lab_default():
    cfg = load_config("configs/indoor_mobility.yaml")
    assert cfg.profile == "indoor_mobility"
    assert cfg.features.ris is True
    assert cfg.network.ris_host == "192.168.10.123"
    assert cfg.network.xapp_port == 8081


def test_csv_header_stable():
    from pyoranris.data.experiment_logger import CSV_HEADER

    assert CSV_HEADER == [
        "timestamp",
        "update_latency",
        "RSRP",
        "RIS_index",
        "RX_index",
        "RIS_Angle",
        "RX_Angle",
    ]
