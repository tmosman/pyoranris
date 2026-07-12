"""DearPyGui front-end — talks only to Controller (no device/socket logic)."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyoranris.controllers.controller import Controller

log = logging.getLogger(__name__)


class DearPyGuiApp:
    def __init__(self, controller: "Controller"):
        self.controller = controller

    def _theme_button(self, dpg):
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
        return theme

    def run(self) -> None:
        try:
            import dearpygui.dearpygui as dpg
        except ImportError as exc:
            raise SystemExit(
                "DearPyGui is required for the GUI. Install with:\n"
                '  pip install -e ".[gui]"'
            ) from exc

        cfg = self.controller.cfg
        btn_theme = None
        dpg.create_context()

        font_path = cfg.devices.font_path
        large_font = None
        if font_path and os.path.exists(font_path):
            with dpg.font_registry():
                large_font = dpg.add_font(font_path, 22)

        with dpg.theme() as red_line_theme:
            with dpg.theme_component(dpg.mvLineSeries):
                dpg.add_theme_color(dpg.mvPlotCol_Line, (255, 0, 0, 255))

        btn_theme = self._theme_button(dpg)

        # ---- RSRP ----
        with dpg.window(label="RSRP Plot", width=960, height=760, pos=(10, 10)):
            with dpg.group(horizontal=True):
                b1 = dpg.add_button(label="Plot RSRP", callback=lambda: self.controller.start_plotting())
                b2 = dpg.add_button(label="Stop RSRP Update", callback=lambda: self.controller.stop_plotting())
                dpg.bind_item_theme(b1, btn_theme)
                dpg.bind_item_theme(b2, btn_theme)
            with dpg.group(horizontal=True):
                dpg.add_text("Current RSRP:")
                dpg.add_text("", tag="rsrp_display", color=(255, 0, 0))
                dpg.add_text("   Monitoring:")
                dpg.add_text("", tag="monitor_display", color=(255, 140, 0))
            with dpg.plot(label="RSRP Real-time Plot", height=640, width=940):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="Iteration", tag="x_axis_rsrp")
                y = dpg.add_plot_axis(dpg.mvYAxis, label="RSRP (dBm)", tag="y_axis_rsrp")
                dpg.set_axis_limits(y, -120.0, -60.0)
                dpg.add_line_series([], [], label="RSRP", parent=y, tag="rsrp_series")

        # ---- Beams ----
        with dpg.window(label="Beams Plot Window", width=860, height=760, pos=(985, 10)):
            bclear = dpg.add_button(label="Clear Beam Plot", callback=lambda: self.controller.clear_series())
            dpg.bind_item_theme(bclear, btn_theme)
            with dpg.group(horizontal=True):
                dpg.add_text("Current RIS Beam:")
                dpg.add_text("", tag="ris_display", color=(255, 0, 0))
                dpg.add_text("   Current RX Beam:")
                dpg.add_text("", tag="rx_display", color=(255, 0, 0))
            with dpg.plot(label="Beam Index Plot", height=640, width=840):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="Iteration", tag="x_axis_beam")
                y_ris = dpg.add_plot_axis(dpg.mvYAxis, label="RIS Angle (°)", tag="y_axis_ris")
                y_rx = dpg.add_plot_axis(dpg.mvYAxis2, label="RX Angle (°)", tag="y_axis_rx")
                dpg.set_axis_limits(y_ris, 10, 70)
                dpg.set_axis_limits(y_rx, -30, 30)
                dpg.add_line_series([], [], label="RIS Beam", parent=y_ris, tag="ris_series")
                dpg.add_line_series([], [], label="RX Beam", parent=y_rx, tag="rx_series")
                dpg.bind_item_theme("rx_series", red_line_theme)

        # ---- xApp ----
        with dpg.window(label="xApp Server", width=380, height=220, pos=(10, 785)):
            with dpg.group(horizontal=True):
                dpg.add_button(label="Start", callback=lambda: self._xapp_start())
                dpg.add_button(label="Stop", callback=lambda: self._xapp_stop())
                dpg.add_text("(Status):", tag="server_status_text")
            dpg.add_text("Monitoring KPIs:", tag="xApp_status_text")
            with dpg.group(horizontal=True):
                dpg.add_button(label="Start ", callback=lambda: self.controller.start_xapp_monitor())
                dpg.add_button(label="Stop ", callback=lambda: self.controller.stop_xapp_monitor())
                dpg.add_button(label="EXIT", callback=lambda: self.controller.exit_xapp_monitor())
            with dpg.group(horizontal=True):
                dpg.add_text("Data Collection:")
                dpg.add_button(
                    label="Capture Sample",
                    callback=lambda: self._run_bg(self.controller.joint_beamsweeping),
                )

        # ---- Beam sweeping / mobility ----
        with dpg.window(label="Beam Sweeping", width=380, height=220, pos=(400, 785)):
            with dpg.group(horizontal=True):
                dpg.add_button(label="RIS Beam Sweeping", callback=lambda: self.controller.set_beamsweep(True))
                dpg.add_button(label="Terminate", callback=lambda: self.controller.set_beamsweep(False))
            dpg.add_text("Experiment Status:", tag="bs_status_text")
            dpg.add_text("Mobility Test Status:", tag="mobility_status_text")
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Joint BS",
                    callback=lambda: self._run_bg(self.controller.joint_beamsweeping),
                )
                dpg.add_button(label="Activate Test", callback=lambda: self.controller.set_mobility(True))
                dpg.add_button(label="Deactivate", callback=lambda: self.controller.set_mobility(False))

        # ---- Robot ----
        with dpg.window(label="Robot Control", width=350, height=220, pos=(790, 785)):
            dpg.add_text("Direction [1-> FWD  -1 -> BWD]")
            dpg.add_input_int(label="Enter (-1/1)", width=150, tag="robot_dir", default_value=1)
            dpg.add_text("Stop ROBOT [1]")
            dpg.add_input_int(label="Enter (1/0)", width=150, tag="robot_stop", default_value=1)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Move", callback=lambda: self._robot_move())
                dpg.add_button(label="Reset", callback=lambda: self._robot_reset())
                dpg.add_text("—", tag="robot_result")

        # ---- Set beams ----
        with dpg.window(label="Set RIS/UE Index Values", width=350, height=220, pos=(1150, 785)):
            dpg.add_input_int(label="RIS Beam Index", width=150, tag="ris_input", default_value=160)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Set index", callback=lambda: self._set_ris())
                dpg.add_text("—", tag="ris_result")
            dpg.add_input_int(label="UE Beam Index", width=150, tag="ue_input", default_value=5)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Set beam", callback=lambda: self._set_ue())
                dpg.add_text("—", tag="ue_result")

        # ---- OAI nrUE ----
        with dpg.window(label="OAI nrUE Control", width=335, height=220, pos=(1510, 785)):
            with dpg.group(horizontal=True):
                dpg.add_button(label="Start nrUE", callback=lambda: self.controller.start_ue_session())
                dpg.add_button(label="Stop nrUE", callback=lambda: self.controller.stop_ue_session())
                dpg.add_button(label="Exit", callback=lambda: self.controller.exit_ue_session())
            with dpg.group(horizontal=True):
                dpg.add_button(label="Get UE IP", callback=lambda: self.controller.get_ue_ip())
                dpg.add_button(label="Update UE IP", callback=lambda: self.controller.update_ue_ip())
            dpg.add_text("Experiment Status:", tag="oai_status_text")
            dpg.add_text(f"Profile: {cfg.profile}", tag="profile_text")
            if self.controller.snapshot.log_path:
                dpg.add_text(f"Log: {self.controller.snapshot.log_path}", wrap=300)

        if large_font is not None:
            dpg.bind_font(large_font)

        dpg.set_exit_callback(lambda: self.controller.stop_plotting())
        dpg.create_viewport(title=f"Evaluation Console [RIS-ORAN] [{cfg.profile}]", width=1860, height=1020)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_frame_callback(1, lambda: self._tick(dpg))
        dpg.start_dearpygui()
        dpg.destroy_context()

    def _run_bg(self, fn) -> None:
        import threading

        threading.Thread(target=fn, daemon=True).start()

    def _xapp_start(self) -> None:
        msg = self.controller.start_xapp_server()
        self.controller._set(xapp_status=msg)

    def _xapp_stop(self) -> None:
        msg = self.controller.stop_xapp_server()
        self.controller._set(xapp_status=msg)

    def _robot_move(self) -> None:
        import dearpygui.dearpygui as dpg

        self.controller.set_robot_inputs(dpg.get_value("robot_dir"), dpg.get_value("robot_stop"))
        dpg.set_value("robot_result", self.controller.move_robot())

    def _robot_reset(self) -> None:
        import dearpygui.dearpygui as dpg

        dpg.set_value("robot_stop", 0)
        dpg.set_value("robot_result", self.controller.reset_robot())

    def _set_ris(self) -> None:
        import dearpygui.dearpygui as dpg

        beam = self.controller.set_ris_beam(dpg.get_value("ris_input"))
        dpg.set_value("ris_result", f"Current Index: {beam}")

    def _set_ue(self) -> None:
        import dearpygui.dearpygui as dpg

        beam = self.controller.set_ue_beam(dpg.get_value("ue_input"))
        dpg.set_value("ue_result", f"Current Index: {beam}")

    def _tick(self, dpg) -> None:
        try:
            snap = self.controller.get_snapshot()
            if snap.current_rsrp == snap.current_rsrp:  # not NaN
                dpg.set_value("rsrp_display", f"{snap.current_rsrp:.1f} dBm")
            dpg.set_value("monitor_display", snap.monitor_msg)
            dpg.set_value("bs_status_text", f"Experiment Status: {snap.bs_status}")
            dpg.set_value(
                "mobility_status_text",
                f"Mobility Test Status: {'Active' if snap.mobility_active else 'Not Active'}",
            )
            dpg.set_value("server_status_text", f"(Status): {snap.xapp_status}")
            dpg.set_value("xApp_status_text", f" Monitoring KPIs: {snap.xapp_status}")
            dpg.set_value("oai_status_text", f"Experiment Status: {snap.oai_status}")

            if snap.current_ris_beam is not None:
                dpg.set_value("ris_display", f"{snap.current_ris_beam}")
            if snap.current_rx_index is not None:
                dpg.set_value("rx_display", f"{snap.current_rx_index}")

            n = len(snap.rsrp_series)
            if n:
                xs = list(range(n))
                dpg.set_value("rsrp_series", [xs, snap.rsrp_series])
                dpg.set_axis_limits("x_axis_rsrp", max(0, n - 200), max(1, n))
                dpg.set_value("ris_series", [xs, snap.ris_angle_series])
                dpg.set_value("rx_series", [xs, snap.rx_angle_series])
                dpg.set_axis_limits("x_axis_beam", max(0, n - 200), max(1, n))
        finally:
            if dpg.is_dearpygui_running():
                dpg.set_frame_callback(dpg.get_frame_count() + 10, lambda: self._tick(dpg))
