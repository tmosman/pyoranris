# Indoor mobility (legacy binary xApp path)

DearPyGui profile for the original MILCOM indoor demo: binary KPI ingest on `:8081`, beam plots, RIS TCP, and flexric `xapp_kpm_rc` launched via the `:5005` monitor.

## Run

```bash
pyoranris run -c configs/indoor_mobility.yaml
```

With `auto_start_xapp_monitor: true`, pyoranris starts the monitor server automatically. Otherwise run it manually:

```bash
pyoranris-xapp-monitor \
  --xapp-bin ~/Fall_2024/October_12th/oai/openair2/E2AP/flexric/build/examples/xApp/c/kpm_rc/xapp_kpm_rc \
  --cwd ~/Fall_2024/October_12th/oai/openair2/E2AP/flexric
```

## GUI workflow

1. **xApp server → Start** — pyoranris listens on `:8081` for KPI TCP
2. **Monitoring KPIs → Start** — monitor server launches `xapp_kpm_rc` (streams to `:8081`)
3. **Plot RSRP** — begin plotting

You can **Stop / Start** Monitoring KPIs without restarting the `:8081` server. **EXIT** stops `xapp_kpm_rc` only; the monitor server on `:5005` stays up.

## Monitor commands (TCP :5005)

| Command | Action |
|---------|--------|
| `START` | Stop any running `xapp_kpm_rc`, launch fresh |
| `STOP` | Stop managed `xapp_kpm_rc` |
| `STATUS` | `[ACK] running` or `[ACK] stopped` |
| `EXIT` | Stop `xapp_kpm_rc` (server keeps listening) |

## Config (`configs/indoor_mobility.yaml`)

```yaml
features:
  auto_start_xapp_monitor: true

lab_ops:
  xapp_kpm_rc_bin: ".../xapp_kpm_rc"
  xapp_monitor_cwd: ".../flexric"
```

## Migration from `xApp_tcp_server.py`

The old flexric script is replaced by `pyoranris.lab.xapp_monitor_server`. Key fixes:

- **EXIT** no longer kills the monitor server
- **STATUS** for GUI health checks
- CLI args for host, port, binary path, cwd

Long-term, consider `configs/kpm_mac_rsrp.yaml` (no `:5005` middleman).
