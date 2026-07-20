# Lab setup (template)

Replace paths below with your machine's OAI / FlexRIC / CN install locations.
Do **not** commit personal absolute paths into Python code — keep them here or in a private notes file.

## pyoranris GUI (X11)

Fresh SSH or `sudo` shells often lack `DISPLAY`, which breaks DearPyGui/GLFW.

**Option 1 — config** (enabled in `configs/lab_default.yaml`):

```yaml
gui:
  display: ""              # auto from `who` / :0, or set ":0.0"
  auto_detect_display: true
  auto_xhost: true
  xhost_user: ""           # use "root" if sudo without SUDO_USER
```

Then run as usual: `pyoranris run -c configs/indoor_mobility.yaml`

**Option 2 — wrapper script**:

```bash
chmod +x scripts/run_gui.sh
./scripts/run_gui.sh -c configs/indoor_mobility.yaml
```

**Option 3 — manual** (if `xhost` must run from your desktop session):

```bash
who                    # note display, e.g. :0
export DISPLAY=:0.0
xhost +si:localuser:root   # or your login user when not using sudo
pyoranris run -c configs/indoor_mobility.yaml
```

Env overrides: `PYORANRIS_DISPLAY`, `PYORANRIS_XHOST_USER`.

## Core network stack

### nr-gNB

```bash
cd <OAI_RAN_BUILD>/build
sudo ./nr-softmodem -O <path-to>/gnb.sa.band78.fr1.106PRB.usrpb210.conf \
  --gNBs.[0].min_rxtxtime 6 --sa -E -d
```

### near-RT RIC

```bash
cd <FLEXRIC_ROOT>
./build/examples/ric/nearRT-RIC
```

### xApp TCP bridge

```bash
cd <FLEXRIC_ROOT>
python xApp_tcp_server.py
```

### 5G Core

```bash
./start_oai_cn5g.sh
# or
cd <OAI_CN5G> && docker compose up -d
```

## EVK02004 (Sivers)

```bash
# decrypt / power sequence per your lab
conda activate oran_ris   # if your lab still uses this env
cd <EVK_SCRIPTS>
python -i ./api_drivers/evk.py
# select SN, repeat for second board
python evks_script_demo.py
```

## pyoranris GUI

```bash
cd <PYORANRIS_CLONE>
source .venv/bin/activate
# edit configs/indoor_mobility.yaml hosts for this VLAN
pyoranris run -c configs/indoor_mobility.yaml
```

## Checklist for a new PC

1. Python 3.10+
2. Clone repo, `pip install -e ".[gui,dev]"`
3. `pyoranris run -c configs/offline_sim.yaml` works
4. Copy `configs/lab_default.yaml` → personal override; set IPs
5. Confirm VLAN / firewall allows RIS / EVK / xApp ports
6. Marvelmind: user in `dialout`, device path matches `devices.marvelmind_tty`
