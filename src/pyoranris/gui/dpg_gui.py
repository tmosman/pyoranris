"""Minimal DearPyGui shell — Phase 1 scaffold (full demo GUI comes in Phase 2)."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class DearPyGuiApp:
    def __init__(self, controller):
        self.controller = controller

    def run(self) -> None:
        try:
            import dearpygui.dearpygui as dpg
        except ImportError as exc:
            raise SystemExit(
                "DearPyGui is required for the GUI. Install with:\n"
                '  pip install -e ".[gui]"'
            ) from exc

        cfg = self.controller.cfg
        dpg.create_context()
        dpg.create_viewport(title=f"pyoranris [{cfg.profile}]", width=900, height=520)

        with dpg.window(label="pyoranris", width=880, height=480):
            dpg.add_text(f"Profile: {cfg.profile}")
            dpg.add_text(
                "Offline simulator"
                if cfg.features.simulate_rsrp
                else f"RSRP port {cfg.network.rsrp_port}"
            )
            dpg.add_separator()
            dpg.add_button(
                label="Start Beam Sweep",
                callback=lambda: self.controller.start_beam_sweep(),
            )
            dpg.add_button(
                label="Stop Beam Sweep",
                callback=lambda: self.controller.stop_beam_sweep(),
            )
            dpg.add_text(default_value="Status: Idle", tag="status_text")
            dpg.add_text(default_value="RSRP: —", tag="rsrp_text")
            if self.controller.logger:
                dpg.add_text(f"Log: {self.controller.logger.csv_path}")

        def _tick():
            try:
                dpg.set_value("status_text", f"Status: {self.controller.status}")
                # Non-blocking peek: drain one sample if available
                try:
                    vals = self.controller.data_q.get_nowait()
                    dpg.set_value("rsrp_text", f"RSRP: {float(vals[0]):.2f} dBm")
                except Exception:
                    pass
            finally:
                if dpg.is_dearpygui_running():
                    dpg.set_frame_callback(dpg.get_frame_count() + 15, _tick)

        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_frame_callback(1, _tick)
        dpg.start_dearpygui()
        dpg.destroy_context()
