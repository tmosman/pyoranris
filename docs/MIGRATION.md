# Migration map

How legacy files map into the package.

| Legacy | Destination | Status |
|--------|-------------|--------|
| Hardcoded IPs / flags in `TCPClientGUI.__init__` | `configs/*.yaml` + `config.py` | Done |
| `CONSTANTS` | `models/constants.py` | Done |
| `BeamIndexOptimizer*` | `algorithms/beam_optimizer.py` | Done |
| RSRP drop monitor / angle map | `algorithms/mobility.py` | Done |
| `TCP_Interface` ACK methods | `net/lab_tcp.py` | Done |
| Generic TCP | `net/tcp_interface.py` | Done |
| `xAppServer` | `net/xapp_server.py` | Done |
| `cameraTCPServer` | `net/camera_server.py` | Done |
| CSV / experiment folders | `data/experiment_logger.py` | Done |
| RIS TCP | `devices/ris.py` | Done |
| UE EVK (rpyc) | `devices/ue_evk.py` | Done |
| Redis robot | `devices/robot.py` | Done |
| Marvelmind | `devices/marvelmind_device.py` | Done |
| `robot_detector.py` / ZED YOLO | `vision/` | Deferred (optional) |
| DearPyGui windows | `gui/dpg_gui.py` | Done (Phase 2) |
| Mobility / beam update loop | `controllers/controller.py` | Done (Phase 2) |

## Phase 2 complete

1. Config-driven feature flags — no IPs in GUI code
2. `ExperimentLogger` wired from the KPI receive loop
3. Device adapters for RIS / UE / robot / Marvelmind / xApp / camera
4. Mobility + joint BS live in `Controller` (no DearPyGui imports)
5. GUI only polls `RuntimeSnapshot` and calls controller methods

## Phase 3A complete — combined KPM + SRS

- Profile `configs/kpm_srs.yaml` runs both TCP clients (`:8081` + `:8082`)
- Dual receive threads + dual CSV logs (`*_kpm.csv`, `*_srs.csv`)
- Combined DearPyGui layout (RSRP/SINR, RIS angle, CFR/CIR)
- See `docs/KPM_SRS.md`

## Remaining polish (Phase 3B+)

- ZED / YOLO vision path
- iperf subprocess controls
- Quectel modem UI branch
- Unit tests for binary xApp packet unpacking
- Enable `features.mobility_reopt: true` when ready (frozen demo kept this off)
