# SRS CIR / CFR in DearPyGui (replaces matplotlib srs_cir_tcp_plot.py)

## Roles

| Process | Role | Port |
|---------|------|------|
| `xapp_srs_ind --srs-cir-tcp 127.0.0.1:8082` | TCP **server** | 8082 |
| `pyoranris` (`configs/srs_cir.yaml`) | TCP **client** + CFR/CIR GUI | connects to 8082 |

Wire format (newline text):

```text
META collect_us sfn slot rnti ue_id Ng Nu n_fft peak_cfr_bin peak_cfr_mag
CFR  collect_us sfn slot rnti ant n_bins i0 q0 i1 q1 ...
```

CIR is computed client-side: `fftshift(abs(ifft(CFR)))`.

## Run

```bash
# After CN + RIC + gNB + UE attach:
SRS_CIR_TCP_MAX_BINS=1536 XAPP_DURATION=-1 \
  ~/Program_scripts/flexric_scripts/oai-flexric.sh start xapp-srs

cd /path/to/pyoranris
source .venv/bin/activate
pip install -e ".[gui]"
pyoranris run -c configs/srs_cir.yaml
```

In the GUI:

1. Optional: **Start xapp-srs**
2. **Connect & Plot** (auto-connects if `auto_connect_srs_cir: true`)
3. Top plot: blue = CFR |H| vs subcarrier bin
4. Bottom plot: red = CIR |h| vs fftshifted tap

## One xApp at a time

Use either `configs/kpm_mac_rsrp.yaml` (:8081) **or** `configs/srs_cir.yaml` (:8082) in a given GUI session.
Both xApps can run on the lab simultaneously, but each pyoranris profile plots one stream.

## Config knobs

```yaml
network:
  srs_port: 8082
lab_ops:
  srs_max_bins: 1536
  srs_fft_size: 0   # 0 = use META n_fft
plot:
  cfr_ylim: [0.0, 0.0]   # ymax<=ymin → auto-scale
  cir_ylim: [0.0, 0.0]
  srs_ylim_floor: 1.0
```

Env: `PYORANRIS_SRS_PORT`.
