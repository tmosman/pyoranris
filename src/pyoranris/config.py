"""Load YAML configs with optional extends + environment overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

import yaml


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


@dataclass
class FeaturesConfig:
    xapp_server: bool = False
    xapp_client: bool = False
    # KPM xapp_kpm_moni text TCP (--mac-rsrp-tcp). GUI is client; xApp is server.
    mac_rsrp_tcp: bool = False
    ris: bool = False  # legacy TCP RIS ACK client
    ris_rest: bool = False  # POST JSON to REST beam apply API
    ue_evk: bool = False
    initialize_ue_beams: bool = False
    marvelmind: bool = False
    zed_server: bool = False
    zed_client: bool = False
    robot_redis: bool = False
    gps: bool = False
    quectel: bool = False
    record_mobility: bool = True
    data_collection: bool = False
    simulate_rsrp: bool = False
    mobility_reopt: bool = False  # apply joint_bs on RSRP drop (off in frozen demo)
    auto_start_xapp: bool = False
    # Start MacRsrpTcpClient when GUI starts (KPM profile)
    auto_connect_mac_rsrp: bool = False
    # POST default RIS beam at startup so angle plot tracks from first sample
    auto_apply_ris_on_start: bool = False


@dataclass
class PlotConfig:
    rsrp_ylim: list[float] = field(default_factory=lambda: [-90.0, -40.0])
    sinr_ylim: list[float] = field(default_factory=lambda: [-20.0, 50.0])
    ris_index_ylim: list[float] = field(default_factory=lambda: [0.0, 21.0])
    ris_angle_ylim: list[float] = field(default_factory=lambda: [20.0, 60.0])
    max_points: int = 600


@dataclass
class LabOpsConfig:
    flexric_script: str = "~/Program_scripts/flexric_scripts/oai-flexric.sh"
    kpm_report_period_ms: int = 100
    xapp_duration: int = -1


@dataclass
class NetworkConfig:
    host: str = "127.0.0.1"
    xapp_port: int = 8081
    xapp_monitor_port: int = 5005
    rsrp_port: int = 10000
    ris_host: str = "192.168.10.123"
    ris_port: int = 9999
    # REST RIS controller (POST {"index": N})
    ris_rest_url: str = "http://localhost:8080/api/beam/apply"
    ue_evk_host: str = "192.168.10.102"
    ue_evk_port: int = 9999
    ue_laptop_host: str = "192.168.10.114"
    ue_oai_port: int = 5001
    gps_port: int = 9991
    camera_host: str = "192.168.1.128"
    camera_port: int = 9908
    jetson_host: str = "192.168.1.116"
    jetson_port: int = 9999
    redis_port: int = 6379
    rpyc_rx_port: int = 18814
    rpyc_tx_port: int = 18815


@dataclass
class DevicesConfig:
    marvelmind_tty: str = "/dev/ttyACM0"
    marvelmind_baud: int = 115200
    font_path: str = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


@dataclass
class BeamsConfig:
    max_ris_index: int = 182
    # Applied at startup when auto_apply_ris_on_start is true
    default_ris_index: int = 1
    beam_interval: int = 1
    rx_angles: list[float] = field(
        default_factory=lambda: [-27, -21, -15, -9, -3, 0, 3, 9, 15, 21, 27]
    )
    window_len: int = 5
    update_window: int = 1001
    # Linear map for compact RIS panels (KPM): index 0..max → angle_min..angle_max
    ris_angle_min: float = 20.0
    ris_angle_max: float = 60.0


@dataclass
class LoggingConfig:
    root_dir: str = "data"
    coverage_subdir: str = "Coverage_Datasets"


@dataclass
class AppConfig:
    profile: str = "lab_default"
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    devices: DevicesConfig = field(default_factory=DevicesConfig)
    beams: BeamsConfig = field(default_factory=BeamsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    plot: PlotConfig = field(default_factory=PlotConfig)
    lab_ops: LabOpsConfig = field(default_factory=LabOpsConfig)


def _from_mapping(cls, data: dict[str, Any] | None):
    if not data:
        return cls()
    allowed = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in allowed})


def _load_yaml_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    if "extends" in raw:
        parent_name = raw.pop("extends")
        parent_path = path.parent / parent_name
        parent = _load_yaml_file(parent_path)
        raw = _deep_merge(parent, raw)
    return raw


def _apply_env(cfg: AppConfig) -> AppConfig:
    """Optional overrides: PYORANRIS_RIS_HOST, PYORANRIS_XAPP_PORT, etc."""
    mapping = {
        "PYORANRIS_HOST": ("network", "host", str),
        "PYORANRIS_XAPP_HOST": ("network", "host", str),
        "PYORANRIS_XAPP_PORT": ("network", "xapp_port", int),
        "PYORANRIS_RSRP_PORT": ("network", "rsrp_port", int),
        "PYORANRIS_RIS_HOST": ("network", "ris_host", str),
        "PYORANRIS_RIS_PORT": ("network", "ris_port", int),
        "PYORANRIS_RIS_REST_URL": ("network", "ris_rest_url", str),
        "PYORANRIS_UE_EVK_HOST": ("network", "ue_evk_host", str),
        "PYORANRIS_DATA_ROOT": ("logging", "root_dir", str),
        "PYORANRIS_MARVELMIND_TTY": ("devices", "marvelmind_tty", str),
    }
    for env_key, (section, attr, caster) in mapping.items():
        if env_key in os.environ:
            setattr(getattr(cfg, section), attr, caster(os.environ[env_key]))
    return cfg


def load_config(path: str | Path | None = None) -> AppConfig:
    if path is None:
        path = _repo_root() / "configs" / "offline_sim.yaml"
    path = Path(path)
    if not path.is_absolute():
        candidate = Path.cwd() / path
        path = candidate if candidate.exists() else _repo_root() / path
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    raw = _load_yaml_file(path)
    cfg = AppConfig(
        profile=raw.get("profile", path.stem),
        features=_from_mapping(FeaturesConfig, raw.get("features")),
        network=_from_mapping(NetworkConfig, raw.get("network")),
        devices=_from_mapping(DevicesConfig, raw.get("devices")),
        beams=_from_mapping(BeamsConfig, raw.get("beams")),
        logging=_from_mapping(LoggingConfig, raw.get("logging")),
        plot=_from_mapping(PlotConfig, raw.get("plot")),
        lab_ops=_from_mapping(LabOpsConfig, raw.get("lab_ops")),
    )
    return _apply_env(cfg)


def describe_features(cfg: AppConfig) -> list[str]:
    lines = [f"profile={cfg.profile}"]
    for f in fields(cfg.features):
        lines.append(f"  {f.name}={getattr(cfg.features, f.name)}")
    return lines
