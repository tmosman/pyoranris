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
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 6)
        return theme

    @staticmethod
    def _ffill(values) -> list[float]:
        """Forward-fill NaNs so DearPyGui gets a continuous step-hold series."""
        out: list[float] = []
        last: float | None = None
        for v in values:
            fv = float(v)
            if fv == fv:
                last = fv
            out.append(last if last is not None else float("nan"))
        # Drop leading NaNs for DPG; if all NaN, return empty
        if not out or all(x != x for x in out):
            return []
        if out[0] != out[0]:
            first = next(x for x in out if x == x)
            out = [first if x != x else x for x in out]
        return out

    def run(self) -> None:
        try:
            import dearpygui.dearpygui as dpg
        except ImportError as exc:
            raise SystemExit(
                "DearPyGui is required for the GUI. Install with:\n"
                '  pip install -e ".[gui]"'
            ) from exc

        cfg = self.controller.cfg
        kpm = cfg.features.mac_rsrp_tcp
        dpg.create_context()

        font_path = cfg.devices.font_path
        large_font = None
        if font_path and os.path.exists(font_path):
            with dpg.font_registry():
                large_font = dpg.add_font(font_path, 20)

        with dpg.theme() as red_line_theme:
            with dpg.theme_component(dpg.mvLineSeries):
                dpg.add_theme_color(
                    dpg.mvPlotCol_Line, (220, 60, 60, 255), category=dpg.mvThemeCat_Plots
                )
                dpg.add_theme_style(
                    dpg.mvPlotStyleVar_LineWeight, 2.0, category=dpg.mvThemeCat_Plots
                )

        with dpg.theme() as blue_line_theme:
            with dpg.theme_component(dpg.mvLineSeries):
                dpg.add_theme_color(
                    dpg.mvPlotCol_Line, (50, 110, 255, 255), category=dpg.mvThemeCat_Plots
                )
                dpg.add_theme_style(
                    dpg.mvPlotStyleVar_LineWeight, 2.0, category=dpg.mvThemeCat_Plots
                )

        with dpg.theme() as orange_line_theme:
            with dpg.theme_component(dpg.mvLineSeries):
                dpg.add_theme_color(
                    dpg.mvPlotCol_Line, (230, 140, 40, 255), category=dpg.mvThemeCat_Plots
                )
                dpg.add_theme_style(
                    dpg.mvPlotStyleVar_LineWeight, 2.0, category=dpg.mvThemeCat_Plots
                )

        # Matplotlib-like dual-axis label colors
        with dpg.theme() as blue_axis_theme:
            with dpg.theme_component(dpg.mvPlotAxis):
                dpg.add_theme_color(
                    dpg.mvPlotCol_AxisText, (50, 110, 255, 255), category=dpg.mvThemeCat_Plots
                )
                dpg.add_theme_color(
                    dpg.mvPlotCol_AxisTick, (50, 110, 255, 255), category=dpg.mvThemeCat_Plots
                )
        with dpg.theme() as red_axis_theme:
            with dpg.theme_component(dpg.mvPlotAxis):
                dpg.add_theme_color(
                    dpg.mvPlotCol_AxisText, (220, 60, 60, 255), category=dpg.mvThemeCat_Plots
                )
                dpg.add_theme_color(
                    dpg.mvPlotCol_AxisTick, (220, 60, 60, 255), category=dpg.mvThemeCat_Plots
                )

        btn_theme = self._theme_button(dpg)

        if kpm:
            self._build_kpm_layout(
                dpg,
                btn_theme,
                blue_line_theme,
                red_line_theme,
                orange_line_theme,
                blue_axis_theme,
                red_axis_theme,
            )
            title = f"KPM MAC RSRP/SINR [{cfg.profile}]"
            viewport = (1860, 1010)
        else:
            self._build_demo_layout(dpg, btn_theme, blue_line_theme, red_line_theme)
            title = f"Evaluation Console [RIS-ORAN] [{cfg.profile}]"
            viewport = (1860, 1020)

        if large_font is not None:
            dpg.bind_font(large_font)

        dpg.set_exit_callback(lambda: self.controller.stop_plotting())
        dpg.create_viewport(title=title, width=viewport[0], height=viewport[1])
        dpg.setup_dearpygui()
        dpg.show_viewport()
        if kpm:
            try:
                dpg.maximize_viewport()
            except Exception:
                pass
        dpg.set_frame_callback(1, lambda: self._tick(dpg))
        dpg.start_dearpygui()
        dpg.destroy_context()

    # ------------------------------------------------------------------
    # KPM-only clean layout (matplotlib replacement)
    # ------------------------------------------------------------------
    def _build_kpm_layout(
        self, dpg, btn_theme, blue_theme, red_theme, orange_theme, blue_axis_theme, red_axis_theme
    ) -> None:
        cfg = self.controller.cfg
        rsrp_lo, rsrp_hi = cfg.plot.rsrp_ylim
        sinr_lo, sinr_hi = cfg.plot.sinr_ylim
        ang_lo, ang_hi = cfg.plot.ris_angle_ylim

        # Matched window + plot geometry for RSRP and RIS panels
        win_w, win_h = 910, 760
        plot_w, plot_h = 890, 660
        gap = 10

        # Primary KPI plot
        with dpg.window(
            label="MacAvgRSRP / MacAvgSINRdB",
            tag="kpm_main_window",
            width=win_w,
            height=win_h,
            pos=(gap, gap),
            no_close=True,
        ):
            with dpg.group(horizontal=True):
                b1 = dpg.add_button(label="Connect & Plot", callback=lambda: self.controller.start_plotting())
                b2 = dpg.add_button(label="Stop", callback=lambda: self.controller.stop_plotting())
                b3 = dpg.add_button(label="Clear", callback=lambda: self.controller.clear_series())
                for b in (b1, b2, b3):
                    dpg.bind_item_theme(b, btn_theme)

            with dpg.group(horizontal=True):
                dpg.add_text("RSRP:")
                dpg.add_text("—", tag="rsrp_display", color=(50, 110, 255))
                dpg.add_text("    SINR:")
                dpg.add_text("—", tag="sinr_display", color=(220, 60, 60))
                dpg.add_text("    ")
                dpg.add_text("waiting for xApp…", tag="monitor_display", color=(255, 170, 60))

            with dpg.plot(label="##kpm_plot", height=plot_h, width=plot_w, tag="main_kpi_plot"):
                dpg.add_plot_legend(location=dpg.mvPlot_Location_NorthWest)
                self._x_axis = dpg.add_plot_axis(
                    dpg.mvXAxis, label="Time from first sample (s)", tag="x_axis_rsrp"
                )
                # Left Y = RSRP (like matplotlib primary)
                self._y_rsrp = dpg.add_plot_axis(
                    dpg.mvYAxis,
                    label="RSRP (dBm)",
                    tag="y_axis_rsrp",
                    no_side_switch=True,
                )
                dpg.bind_item_theme(self._y_rsrp, blue_axis_theme)
                dpg.set_axis_limits(self._y_rsrp, float(rsrp_lo), float(rsrp_hi))
                dpg.add_line_series(
                    [], [], label="MacAvgRSRP", parent=self._y_rsrp, tag="rsrp_series"
                )
                dpg.bind_item_theme("rsrp_series", blue_theme)

                # Right Y = SINR (matplotlib twinax); opposite=True places it on the right
                self._y_sinr = dpg.add_plot_axis(
                    dpg.mvYAxis2,
                    label="SINR (dB)",
                    tag="y_axis_sinr",
                    opposite=True,
                    no_side_switch=True,
                )
                dpg.bind_item_theme(self._y_sinr, red_axis_theme)
                dpg.set_axis_limits(self._y_sinr, float(sinr_lo), float(sinr_hi))
                dpg.add_line_series(
                    [], [], label="MacAvgSINRdB", parent=self._y_sinr, tag="sinr_series"
                )
                dpg.bind_item_theme("sinr_series", red_theme)

        # RIS beam angle — same window and plot size as RSRP panel
        with dpg.window(
            label="RIS Beam Angle",
            tag="kpm_ris_plot_window",
            width=win_w,
            height=win_h,
            pos=(gap + win_w + gap, gap),
            no_close=True,
        ):
            with dpg.group(horizontal=True):
                dpg.add_text(
                    f"Index 0–{int(cfg.beams.max_ris_index)}  →  "
                    f"{float(cfg.beams.ris_angle_min):.0f}–{float(cfg.beams.ris_angle_max):.0f}°",
                    color=(160, 160, 160),
                )

            with dpg.group(horizontal=True):
                dpg.add_text("Index:")
                dpg.add_text("—", tag="ris_index_display", color=(40, 170, 90))
                dpg.add_text("    Angle:")
                dpg.add_text("—", tag="ris_angle_display", color=(230, 140, 40))

            with dpg.plot(label="##ris_beam_plot", height=plot_h, width=plot_w, tag="ris_beam_plot"):
                dpg.add_plot_legend(location=dpg.mvPlot_Location_NorthWest)
                self._x_axis_ris = dpg.add_plot_axis(
                    dpg.mvXAxis, label="Time from first sample (s)", tag="x_axis_ris"
                )
                self._y_ris_ang = dpg.add_plot_axis(
                    dpg.mvYAxis, label="RIS angle (°)", tag="y_axis_ris_ang"
                )
                dpg.set_axis_limits(self._y_ris_ang, float(ang_lo), float(ang_hi))
                dpg.add_line_series(
                    [], [], label="RIS angle", parent=self._y_ris_ang, tag="ris_angle_series"
                )
                dpg.bind_item_theme("ris_angle_series", orange_theme)

        ctrl_y = gap + win_h + gap
        total_w = 2 * win_w + 3 * gap
        ctrl_w = (total_w - 4 * gap) // 3

        # Compact control bar
        with dpg.window(
            label="KPM xApp",
            tag="kpm_controls",
            width=ctrl_w,
            height=170,
            pos=(gap, ctrl_y),
            no_close=True,
        ):
            with dpg.group(horizontal=True):
                b_start = dpg.add_button(label="Start xapp-kpm", callback=lambda: self._xapp_start())
                b_stop = dpg.add_button(label="Stop xapp-kpm", callback=lambda: self._xapp_stop())
                b_stat = dpg.add_button(label="Status", callback=lambda: self.controller.status_kpm_xapp())
                for b in (b_start, b_stop, b_stat):
                    dpg.bind_item_theme(b, btn_theme)
            dpg.add_spacer(height=4)
            dpg.add_text("disconnected", tag="server_status_text", color=(200, 200, 200))
            dpg.add_text(
                f"TCP client → {cfg.network.host}:{cfg.network.xapp_port}",
                tag="xApp_status_text",
            )
            dpg.add_text("Wire: collect_us  ran_ue_id  rsrp_dBm  sinr_dB")

        # RIS REST control
        with dpg.window(
            label="RIS Control",
            tag="kpm_ris",
            width=ctrl_w,
            height=170,
            pos=(gap * 2 + ctrl_w, ctrl_y),
            no_close=True,
        ):
            dpg.add_text(f"POST {cfg.network.ris_rest_url}", wrap=ctrl_w - 20)
            dpg.add_spacer(height=4)
            with dpg.group(horizontal=True):
                dpg.add_input_int(
                    label="Beam index",
                    tag="ris_input",
                    default_value=int(cfg.beams.default_ris_index),
                    width=120,
                    min_value=0,
                    max_value=int(cfg.beams.max_ris_index),
                )
                b_apply = dpg.add_button(label="Apply", callback=lambda: self._apply_ris_rest())
                dpg.bind_item_theme(b_apply, btn_theme)
            dpg.add_spacer(height=4)
            dpg.add_text("Current: —", tag="ris_display")
            dpg.add_text("", tag="ris_result", wrap=ctrl_w - 20)

        with dpg.window(
            label="Session",
            tag="kpm_session",
            width=ctrl_w,
            height=170,
            pos=(gap * 3 + 2 * ctrl_w, ctrl_y),
            no_close=True,
        ):
            dpg.add_text(f"Profile: {cfg.profile}")
            log_path = self.controller.snapshot.log_path or "(logging off)"
            dpg.add_text(f"Log: {log_path}", wrap=ctrl_w - 20, tag="kpm_log_path")
            dpg.add_spacer(height=6)
            dpg.add_text(
                "Blue/Red = RSRP/SINR · Orange = RIS angle",
                color=(160, 160, 160),
            )

    # ------------------------------------------------------------------
    # Full MILCOM demo layout (legacy path)
    # ------------------------------------------------------------------
    def _build_demo_layout(self, dpg, btn_theme, blue_theme, red_theme) -> None:
        cfg = self.controller.cfg
        rsrp_lo, rsrp_hi = -120.0, -60.0

        with dpg.window(label="RSRP Plot", width=960, height=760, pos=(10, 10)):
            with dpg.group(horizontal=True):
                b1 = dpg.add_button(label="Plot RSRP", callback=lambda: self.controller.start_plotting())
                b2 = dpg.add_button(label="Stop RSRP Update", callback=lambda: self.controller.stop_plotting())
                dpg.bind_item_theme(b1, btn_theme)
                dpg.bind_item_theme(b2, btn_theme)
            with dpg.group(horizontal=True):
                dpg.add_text("Current RSRP:")
                dpg.add_text("", tag="rsrp_display", color=(50, 110, 255))
                dpg.add_text("   Monitoring:")
                dpg.add_text("", tag="monitor_display", color=(255, 140, 0))
            with dpg.plot(label="RSRP Real-time Plot", height=640, width=940, tag="main_kpi_plot"):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="Iteration", tag="x_axis_rsrp")
                y = dpg.add_plot_axis(dpg.mvYAxis, label="RSRP (dBm)", tag="y_axis_rsrp")
                dpg.set_axis_limits(y, rsrp_lo, rsrp_hi)
                dpg.add_line_series([], [], label="RSRP", parent=y, tag="rsrp_series")
                dpg.bind_item_theme("rsrp_series", blue_theme)

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
                dpg.bind_item_theme("rx_series", red_theme)

        with dpg.window(label="xApp Server", width=380, height=220, pos=(10, 785)):
            with dpg.group(horizontal=True):
                dpg.add_button(label="Start", callback=lambda: self._xapp_start())
                dpg.add_button(label="Stop", callback=lambda: self._xapp_stop())
                dpg.add_text("", tag="server_status_text")
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

        with dpg.window(label="Robot Control", width=350, height=220, pos=(790, 785)):
            dpg.add_text("Direction [1-> FWD  -1 -> BWD]")
            dpg.add_input_int(label="Enter (-1/1)", width=150, tag="robot_dir", default_value=1)
            dpg.add_text("Stop ROBOT [1]")
            dpg.add_input_int(label="Enter (1/0)", width=150, tag="robot_stop", default_value=1)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Move", callback=lambda: self._robot_move())
                dpg.add_button(label="Reset", callback=lambda: self._robot_reset())
                dpg.add_text("—", tag="robot_result")

        with dpg.window(label="Set RIS/UE Index Values", width=350, height=220, pos=(1150, 785)):
            dpg.add_input_int(label="RIS Beam Index", width=150, tag="ris_input", default_value=160)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Set index", callback=lambda: self._set_ris())
                dpg.add_text("—", tag="ris_result")
            dpg.add_input_int(label="UE Beam Index", width=150, tag="ue_input", default_value=5)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Set beam", callback=lambda: self._set_ue())
                dpg.add_text("—", tag="ue_result")

        with dpg.window(label="OAI nrUE Control", width=335, height=220, pos=(1510, 785)):
            with dpg.group(horizontal=True):
                dpg.add_button(label="Start nrUE", callback=lambda: self.controller.start_ue_session())
                dpg.add_button(label="Stop nrUE", callback=lambda: self.controller.stop_ue_session())
                dpg.add_button(label="Exit", callback=lambda: self.controller.exit_ue_session())
            with dpg.group(horizontal=True):
                dpg.add_button(label="Get UE IP", callback=lambda: self.controller.get_ue_ip())
                dpg.add_button(label="Update UE IP", callback=lambda: self.controller.update_ue_ip())
            dpg.add_text("Experiment Status:", tag="oai_status_text")
            dpg.add_text(f"Profile: {cfg.profile}")
            if self.controller.snapshot.log_path:
                dpg.add_text(f"Log: {self.controller.snapshot.log_path}", wrap=300)

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

    def _apply_ris_rest(self) -> None:
        import dearpygui.dearpygui as dpg

        index = int(dpg.get_value("ris_input"))
        try:
            beam = self.controller.set_ris_beam(index)
            snap = self.controller.get_snapshot()
            if dpg.does_item_exist("ris_display"):
                dpg.set_value("ris_display", f"Current: {beam}")
            if dpg.does_item_exist("ris_result"):
                dpg.set_value("ris_result", snap.ris_status or f"Applied index {beam}")
        except Exception as exc:
            if dpg.does_item_exist("ris_result"):
                dpg.set_value("ris_result", f"Failed: {exc}")

    def _set_ris(self) -> None:
        self._apply_ris_rest()

    def _set_ue(self) -> None:
        import dearpygui.dearpygui as dpg

        beam = self.controller.set_ue_beam(dpg.get_value("ue_input"))
        dpg.set_value("ue_result", f"Current Index: {beam}")

    def _tick(self, dpg) -> None:
        try:
            snap = self.controller.get_snapshot()
            cfg = self.controller.cfg
            kpm = cfg.features.mac_rsrp_tcp

            if snap.current_rsrp == snap.current_rsrp:
                dpg.set_value("rsrp_display", f"{snap.current_rsrp:.1f} dBm")
            if kpm and dpg.does_item_exist("sinr_display"):
                if snap.current_sinr == snap.current_sinr:
                    dpg.set_value("sinr_display", f"{snap.current_sinr:.1f} dB")
                else:
                    dpg.set_value("sinr_display", "—")

            if dpg.does_item_exist("monitor_display"):
                dpg.set_value("monitor_display", snap.monitor_msg or ("connected" if snap.mac_connected else "waiting for xApp…"))

            if kpm:
                conn = "connected" if snap.mac_connected else "waiting for xApp…"
                if dpg.does_item_exist("server_status_text"):
                    dpg.set_value("server_status_text", conn)
                if dpg.does_item_exist("xApp_status_text"):
                    dpg.set_value(
                        "xApp_status_text",
                        f"TCP client → {cfg.network.host}:{cfg.network.xapp_port}  ·  {conn}",
                    )
                if snap.current_ris_beam is not None:
                    ang = snap.current_ris_angle
                    ang_s = f"{ang:.1f}°" if ang == ang else "—"
                    live = f"{snap.current_ris_beam} ({ang_s})"
                    if dpg.does_item_exist("ris_display"):
                        dpg.set_value("ris_display", f"Current: {live}")
                    if dpg.does_item_exist("ris_index_display"):
                        dpg.set_value("ris_index_display", str(snap.current_ris_beam))
                    if dpg.does_item_exist("ris_angle_display"):
                        dpg.set_value("ris_angle_display", ang_s)
                if snap.ris_status and dpg.does_item_exist("ris_result"):
                    # don't clobber a fresh Failed: message every frame unless empty
                    cur = dpg.get_value("ris_result")
                    if not cur or cur.startswith("OK") or cur.startswith("HTTP") or "Applied" in str(cur) or cur.startswith("TCP") or cur.startswith("local"):
                        dpg.set_value("ris_result", snap.ris_status)
            else:
                if dpg.does_item_exist("server_status_text"):
                    dpg.set_value("server_status_text", snap.xapp_status)
                if dpg.does_item_exist("xApp_status_text"):
                    dpg.set_value("xApp_status_text", f"Monitoring KPIs: {snap.xapp_status}")
                if dpg.does_item_exist("bs_status_text"):
                    dpg.set_value("bs_status_text", f"Experiment Status: {snap.bs_status}")
                if dpg.does_item_exist("mobility_status_text"):
                    dpg.set_value(
                        "mobility_status_text",
                        f"Mobility Test Status: {'Active' if snap.mobility_active else 'Not Active'}",
                    )
                if dpg.does_item_exist("oai_status_text"):
                    dpg.set_value("oai_status_text", f"Experiment Status: {snap.oai_status}")
                if snap.current_ris_beam is not None and dpg.does_item_exist("ris_display"):
                    dpg.set_value("ris_display", f"{snap.current_ris_beam}")
                if snap.current_rx_index is not None and dpg.does_item_exist("rx_display"):
                    dpg.set_value("rx_display", f"{snap.current_rx_index}")

            n = len(snap.rsrp_series)
            if n and dpg.does_item_exist("rsrp_series"):
                if kpm and snap.t_rel_series:
                    xs = [float(v) for v in snap.t_rel_series]
                    ys_r = [float(v) if v == v else 0.0 for v in snap.rsrp_series]
                    ys_s = [float(v) if v == v else 0.0 for v in snap.sinr_series]
                    ys_a = self._ffill(snap.ris_angle_series)
                    # DearPyGui expects two sequences; keep lengths matched
                    m = min(len(xs), len(ys_r), len(ys_s))
                    if ys_a:
                        m = min(m, len(ys_a))
                    xs, ys_r, ys_s = xs[-m:], ys_r[-m:], ys_s[-m:]
                    ys_a = ys_a[-m:] if ys_a else []
                    dpg.set_value("rsrp_series", [xs, ys_r])
                    if dpg.does_item_exist("sinr_series"):
                        dpg.set_value("sinr_series", [xs, ys_s])
                    if ys_a and dpg.does_item_exist("ris_angle_series"):
                        dpg.set_value("ris_angle_series", [xs, ys_a])

                    x1 = xs[-1]
                    window_s = 30.0
                    x0 = max(0.0, x1 - window_s)
                    if x1 <= x0:
                        x1 = x0 + 1.0
                    dpg.set_axis_limits(getattr(self, "_x_axis", "x_axis_rsrp"), x0, x1 + 0.05)
                    if dpg.does_item_exist("x_axis_ris"):
                        dpg.set_axis_limits(
                            getattr(self, "_x_axis_ris", "x_axis_ris"), x0, x1 + 0.05
                        )

                    rsrp_lo, rsrp_hi = cfg.plot.rsrp_ylim
                    sinr_lo, sinr_hi = cfg.plot.sinr_ylim
                    dpg.set_axis_limits(
                        getattr(self, "_y_rsrp", "y_axis_rsrp"), float(rsrp_lo), float(rsrp_hi)
                    )
                    if dpg.does_item_exist("y_axis_sinr"):
                        dpg.set_axis_limits(
                            getattr(self, "_y_sinr", "y_axis_sinr"), float(sinr_lo), float(sinr_hi)
                        )
                    if dpg.does_item_exist("y_axis_ris_ang"):
                        ang_lo, ang_hi = cfg.plot.ris_angle_ylim
                        dpg.set_axis_limits(
                            getattr(self, "_y_ris_ang", "y_axis_ris_ang"),
                            float(ang_lo),
                            float(ang_hi),
                        )
                else:
                    xs = list(range(n))
                    dpg.set_value("rsrp_series", [xs, list(snap.rsrp_series)])
                    dpg.set_axis_limits("x_axis_rsrp", max(0, n - 200), max(1, n))
                    if snap.ris_angle_series and dpg.does_item_exist("ris_series"):
                        xs_b = list(range(len(snap.ris_angle_series)))
                        dpg.set_value("ris_series", [xs_b, list(snap.ris_angle_series)])
                        dpg.set_value("rx_series", [xs_b, list(snap.rx_angle_series)])
                        dpg.set_axis_limits("x_axis_beam", max(0, len(xs_b) - 200), max(1, len(xs_b)))
        finally:
            if dpg.is_dearpygui_running():
                dpg.set_frame_callback(dpg.get_frame_count() + 10, lambda: self._tick(dpg))
