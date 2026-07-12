# KPM MAC RSRP / SINR in DearPyGui (replaces matplotlib mac_rsrp_tcp_plot.py)

## Roles

| Process | Role | Port |
|---------|------|------|
| `xapp_kpm_moni --mac-rsrp-tcp 127.0.0.1:8081` | TCP **server** | 8081 |
| `pyoranris` (`configs/kpm_mac_rsrp.yaml`) | TCP **client** + dual-axis GUI | connects to 8081 |

Wire format (newline text):

```text
collectStartTime_us ran_ue_id mac_avg_rsrp_dBm mac_avg_sinr_dB
```

Sentinel `-1000` = missing (plotted as a gap).

## Run

```bash
# After CN + RIC + gNB + UE attach:
KPM_REPORT_PERIOD_MS=100 XAPP_DURATION=-1 \
  ~/Program_scripts/flexric_scripts/oai-flexric.sh start xapp-kpm

cd /home/tmosman/Documents/pyoranris
source .venv/bin/activate
pip install -e ".[gui]"
pyoranris run -c configs/kpm_mac_rsrp.yaml
```

In the GUI:

1. Optional: **Start xapp-kpm** (calls your `oai-flexric.sh`)
2. **Connect & Plot** (auto-connects if `auto_connect_mac_rsrp: true`)
3. Left plot: blue = MacAvgRSRP, red = MacAvgSINRdB
4. Right plot: orange = RIS beam angle (20–60°)
5. **RIS Control → Apply** sets the beam via REST and updates the live angle series
   (on startup, `default_ris_index` is POSTed in the background so the angle plot
   tracks from the first RSRP sample)

CSV is written under `data/run_<UTC_stamp>.csv` with columns:
`timestamp, t_rel_s, ran_ue_id, RSRP, SINR, RIS_index, RIS_Angle, update_latency`.
One CSV per run under `data/` — no subfolders.

## RIS beam index ↔ angle

Compact panel mapping (configurable under `beams:`):

| Index | Angle |
|-------|-------|
| 0 | 20° |
| 21 | 60° |

Linear: `angle = 20 + index * (60-20)/21`.

## Do not mix with legacy MILCOM binary server

`features.xapp_server: true` makes pyoranris *listen* on 8081 for binary `iiii` packets.
KPM mode keeps `xapp_server: false` so the C xApp owns the port.

## Env Y-limits (optional)

Same idea as the matplotlib script — set in YAML under `plot:`:

```yaml
plot:
  rsrp_ylim: [-140.0, -40.0]
  sinr_ylim: [-20.0, 50.0]
  ris_index_ylim: [0.0, 21.0]
  ris_angle_ylim: [20.0, 60.0]
```
