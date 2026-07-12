# pyoranris

Transferable **O-RAN + RIS** indoor demo toolkit: config-driven networking, beam search, experiment logging, and a minimal DearPyGui shell.

This repository is the Phase 0–1 adoption of the MILCOM demo refactor plan. The original working scripts are frozen under [`legacy/`](legacy/) while new code lives in an installable package under [`src/pyoranris/`](src/pyoranris/).

## Quick start (any lab PC)

```bash
git clone https://github.com/tmosman/pyoranris.git
cd pyoranris

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[gui,dev]"

# Verify config (no hardware)
pyoranris show-config -c configs/offline_sim.yaml

# Run offline GUI with simulated RSRP
pyoranris run -c configs/offline_sim.yaml
```

Headless (CI / SSH):

```bash
pyoranris run -c configs/offline_sim.yaml --headless
```

## Config profiles

| File | Purpose |
|------|---------|
| `configs/offline_sim.yaml` | No lab hardware — learn GUI / install check |
| `configs/lab_default.yaml` | IPs/ports frozen from the Jul 2026 working demo |
| `configs/indoor_mobility.yaml` | Mobility demo profile (extends lab defaults) |

Override without editing files:

```bash
export PYORANRIS_RIS_HOST=192.168.10.123
export PYORANRIS_DATA_ROOT=./data
pyoranris show-config -c configs/indoor_mobility.yaml
```

## Package layout

```text
src/pyoranris/
  config.py           # YAML + env loading
  algorithms/         # beam search (pure logic)
  net/                # TCP clients / RSRP server
  devices/            # Marvelmind, etc.
  data/               # experiment CSV / .npy writers
  controllers/        # orchestration (no GUI)
  gui/                # DearPyGui only
legacy/               # Phase-0 frozen originals
docs/GOLDEN_PATH.md   # how the old demo was run
docs/MIGRATION.md     # Phase 2 split map
```

## Tests

```bash
pytest -q
```

## Lab bring-up

gNB / RIC / CN / EVK steps are documented in [`docs/LAB_SETUP.md`](docs/LAB_SETUP.md) (templated — edit for your machine).

## Lab profile (hardware)

```bash
# edit configs/indoor_mobility.yaml hosts for your VLAN
pip install -e ".[lab]"
pyoranris run -c configs/indoor_mobility.yaml
```

Then in the GUI: **Start** (xApp server) → **Plot RSRP**. Optional: **Activate Test** for mobility monitoring.

## KPM MAC RSRP / SINR (replaces matplotlib plot)

```bash
# Terminal A — after RIC/gNB/UE are up
KPM_REPORT_PERIOD_MS=100 XAPP_DURATION=-1 \
  ~/Program_scripts/flexric_scripts/oai-flexric.sh start xapp-kpm

# Terminal B
pyoranris run -c configs/kpm_mac_rsrp.yaml
```

Dual-axis DearPyGui plot (RSRP blue, SINR red). See [`docs/KPM_MAC_RSRP.md`](docs/KPM_MAC_RSRP.md).

RIS beam apply (REST) from the **RIS Control** panel:

```bash
# API expected by the GUI
curl -s -X POST http://localhost:8080/api/beam/apply \
  -H 'Content-Type: application/json' \
  -d '{"index":1}'
```

Override URL with `network.ris_rest_url` or `PYORANRIS_RIS_REST_URL`.

## Status

- **Phase 0** — golden path + legacy freeze — done
- **Phase 1** — installable package + YAML configs + CLI — done
- **Phase 2** — controller / devices / full GUI split — done
- **KPM MAC TCP client** — replaces `mac_rsrp_tcp_plot.py` — done
