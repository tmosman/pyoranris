# Combined KPM + SRS (Phase 3 Option A)

One DearPyGui session for both streams:

| Stream | Port | Plots |
|--------|------|-------|
| KPM MAC RSRP/SINR | 8081 | RSRP (blue) / SINR (red) + RIS angle (orange) |
| SRS CIR/CFR | 8082 | CFR (blue) top, CIR (red) bottom |

## Run

```bash
# After CN + RIC + gNB + UE:
KPM_REPORT_PERIOD_MS=100 XAPP_DURATION=-1 \
  ~/Program_scripts/flexric_scripts/oai-flexric.sh start xapp-kpm

SRS_CIR_TCP_MAX_BINS=1536 XAPP_DURATION=-1 \
  ~/Program_scripts/flexric_scripts/oai-flexric.sh start xapp-srs

pyoranris run -c configs/kpm_srs.yaml
```

Or use the GUI **Start kpm** / **Start srs** buttons.

## Logging

Two CSVs under `data/` (same UTC stamp):

- `run_<stamp>_kpm.csv` — KPI rows
- `run_<stamp>_srs.csv` — SRS META rows (no IQ dump)

## Fallbacks

Single-stream profiles still work:

- `configs/kpm_mac_rsrp.yaml`
- `configs/srs_cir.yaml`
