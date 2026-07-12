# pyoranris

Transferable **O-RAN + RIS** indoor demo toolkit: config-driven networking, beam control, experiment logging, and a DearPyGui evaluation console.

The original working scripts are frozen under [`legacy/`](legacy/). New code lives in an installable package under [`src/pyoranris/`](src/pyoranris/).

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
| `configs/kpm_mac_rsrp.yaml` | **KPM path** — MAC RSRP/SINR + RIS REST beam control |
| `configs/lab_default.yaml` | IPs/ports frozen from the Jul 2026 working demo |
| `configs/indoor_mobility.yaml` | Legacy MILCOM binary xApp mobility profile |

Override without editing files:

```bash
export PYORANRIS_RIS_HOST=192.168.10.123
export PYORANRIS_DATA_ROOT=./data
export PYORANRIS_RIS_REST_URL=http://localhost:8080/api/beam/apply
pyoranris show-config -c configs/kpm_mac_rsrp.yaml
```

## Package layout

```text
src/pyoranris/
  config.py           # YAML + env loading
  algorithms/         # beam search / RIS angle map
  net/                # KPM MAC TCP client, legacy xApp server
  devices/            # RIS REST/TCP, UE EVK, Marvelmind, robot
  data/               # CSV experiment logger (one file per run)
  controllers/        # orchestration (no GUI)
  gui/                # DearPyGui only
legacy/               # Phase-0 frozen originals
docs/GOLDEN_PATH.md   # how the old demo was run
docs/KPM_MAC_RSRP.md  # KPM GUI + wire format
docs/MIGRATION.md     # Phase 2 split map
```

## Tests

```bash
pytest -q
```

## Lab bring-up

gNB / RIC / CN / EVK steps are documented in [`docs/LAB_SETUP.md`](docs/LAB_SETUP.md) (templated — edit for your machine).

## KPM MAC RSRP / SINR + RIS (recommended)

Replaces the matplotlib `mac_rsrp_tcp_plot.py` path.

```bash
# Terminal A — after RIC/gNB/UE are up
KPM_REPORT_PERIOD_MS=100 XAPP_DURATION=-1 \
  ~/Program_scripts/flexric_scripts/oai-flexric.sh start xapp-kpm

# Terminal B — ensure RIS REST API is serving beam apply
pyoranris run -c configs/kpm_mac_rsrp.yaml
```

GUI:

- Left plot: **MacAvgRSRP** (blue, left axis) / **MacAvgSINRdB** (red, right axis)
- Right plot: **RIS beam angle** (orange), mapped from index 0–21 → 20–60°
- On start, `default_ris_index` is POSTed in the background so angle tracking begins with RSRP
- **RIS Control → Apply** changes the beam via REST

CSV per run: `data/run_<UTC_stamp>.csv`  
Columns: `timestamp, t_rel_s, ran_ue_id, RSRP, SINR, RIS_index, RIS_Angle, update_latency`

Manual beam apply (same API the GUI uses):

```bash
curl -s -X POST http://localhost:8080/api/beam/apply \
  -H 'Content-Type: application/json' \
  -d '{"index":1}'
```

Full details: [`docs/KPM_MAC_RSRP.md`](docs/KPM_MAC_RSRP.md).

## Legacy lab profile (binary xApp)

```bash
# edit configs/indoor_mobility.yaml hosts for your VLAN
pip install -e ".[lab]"
pyoranris run -c configs/indoor_mobility.yaml
```

Then in the GUI: **Start** (xApp server) → **Plot RSRP**. Optional: **Activate Test** for mobility monitoring.

Do **not** run this profile together with KPM — both want TCP port 8081.

## Status

- **Phase 0** — golden path + legacy freeze — done
- **Phase 1** — installable package + YAML configs + CLI — done
- **Phase 2** — controller / devices / full GUI split — done
- **KPM MAC TCP client** — RSRP/SINR + RIS angle monitoring — done
