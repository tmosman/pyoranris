# Migration map (Phase 2+)

How legacy files map into the package. Phase 1 scaffolds the packages; Phase 2 moves behavior.

| Legacy | Destination | Status |
|--------|-------------|--------|
| Hardcoded IPs / flags in `TCPClientGUI.__init__` | `configs/*.yaml` + `config.py` | Done (Phase 1) |
| `CONSTANTS` | `models/constants.py` | Done |
| `BeamIndexOptimizer*` | `algorithms/beam_optimizer.py` | Clean + legacy port |
| `TCP_Interface` ACK methods | `net/lab_tcp.py` | Done (API) |
| Generic TCP | `net/tcp_interface.py` | Done |
| `xAppServer` / `BeaconServer` / `cameraTCPServer` | `net/` (split modules) | TODO Phase 2 |
| CSV / experiment folders | `data/experiment_logger.py` | Done |
| `marvelmind.py` | `devices/marvelmind.py` | Copied |
| `robot_detector.py` | `devices/` + `vision/` | TODO |
| DearPyGui windows in `TCPClientGUI` | `gui/dpg_gui.py` | Minimal shell only |
| Mobility / beam update loop | `controllers/controller.py` | Stub sweep only |

## Phase 2 extraction order

1. Config already external — stop editing flags in Python
2. `ExperimentLogger` — wire full demo writes
3. Device adapters: RIS, UE EVK, xApp, Marvelmind
4. Move mobility loop out of GUI callbacks into `Controller`
5. Rebuild DearPyGui against controller methods only

## Rule

Algorithms and protocol parsing must run in tests **without** GUI or hardware.
