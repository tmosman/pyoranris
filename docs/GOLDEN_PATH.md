# Phase 0 — Golden path (frozen Jul 2026)

This records how the **working** MILCOM indoor demo was run before the refactor.
Do not delete `legacy/` until Phase 2 has feature parity.

## Source freeze

| Legacy file | Role |
|-------------|------|
| `INDOORS_MILCOM_DEMO_debugging_v2.py` | Main DearPyGui app (`TCPClientGUI`) |
| `classes_file.py` | CONSTANTS, beam optimizers, TCP/xApp/Beacon servers |
| `marvelmind.py` | Indoor positioning USB hedge |
| `robot_detector.py` | ZED2 + YOLO tracker |
| `Instructions` / `instruction_v2` | Historical bring-up notes (machine-specific paths) |

## Feature flags in the working demo (`__init__`)

As checked into `legacy/INDOORS_MILCOM_DEMO_debugging_v2.py`:

| Flag | Value | Meaning |
|------|-------|---------|
| `xApp_run` | `True` | Local xApp TCP server on `host:8081` |
| `xApp_client` | `True` | Monitor client on port `5005` |
| `RIS_client` | `False` | RIS beam steering (enable when RIS Pi is up) |
| `ue_status` | `False` | UE EVK beam client |
| `position_obj` | `False` | Marvelmind |
| `zed_server` / `ZED2_*` | `False` | Camera path |
| `robot_server` | `False` | Redis robot commands |
| `ue_mobility_record` | `True` | Write `data_log.csv` |

## Network endpoints (lab_default)

| Role | Host | Port |
|------|------|------|
| Local host / xApp | `127.0.0.1` | `8081` |
| xApp monitor | `127.0.0.1` | `5005` |
| RIS (Raspberry Pi) | `192.168.10.123` | `9999` |
| UE EVK | `192.168.10.102` | `9999` |
| UE laptop / OAI UE | `192.168.10.114` | `5001` |
| Camera | `192.168.1.128` | `9908` |
| Jetson | `192.168.1.116` | `9999` |

## CSV schema (do not break)

```text
timestamp, update_latency, RSRP, RIS_index, RX_index, RIS_Angle, RX_Angle
```

Output path pattern:

```text
<data_root>/UE_Mobility/Experiment_at_<UTC_stamp>/data_log.csv
```

## How to run the legacy script (temporary)

Only if you need the full GUI before Phase 2 lands:

```bash
cd legacy
# ensure classes_file.py / marvelmind.py are on PYTHONPATH (same folder)
python INDOORS_MILCOM_DEMO_debugging_v2.py
```

Prefer `pyoranris run -c configs/offline_sim.yaml` for install verification on new PCs.
