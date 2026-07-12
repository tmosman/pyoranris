"""Orchestration layer — no DearPyGui imports."""

from __future__ import annotations

import logging
import queue
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from pyoranris.algorithms.beam_optimizer import BeamIndexOptimizer, BeamIndexOptimizer2, BeamSearch
from pyoranris.algorithms.mobility import RSRPMonitor, index_to_angles
from pyoranris.config import AppConfig
from pyoranris.data.experiment_logger import ExperimentLogger
from pyoranris.devices.marvelmind_device import PositionDevice
from pyoranris.devices.ris import RISDevice
from pyoranris.devices.ris_rest import RISRestClient
from pyoranris.devices.robot import RobotDevice
from pyoranris.devices.ue_evk import UEEvkDevice
from pyoranris.models.constants import Constants
from pyoranris.net.camera_server import CameraTCPServer
from pyoranris.net.lab_tcp import LabTCPClient
from pyoranris.net.mac_rsrp_client import MacKpiSample, MacRsrpTcpClient
from pyoranris.net.xapp_server import XAppServer
from pyoranris.lab.flexric_ops import FlexricKpmLauncher

log = logging.getLogger(__name__)


@dataclass
class RuntimeSnapshot:
    """Thread-safe GUI-facing state (poll from the UI thread)."""

    status: str = "Idle"
    monitor_msg: str = ""
    bs_status: str = ""
    xapp_status: str = ""
    oai_status: str = ""
    mobility_active: bool = False
    plotting: bool = False
    mac_connected: bool = False
    current_rsrp: float = float("nan")
    current_sinr: float = float("nan")
    ran_ue_id: int = 0
    current_ris_beam: int | None = None
    current_rx_index: int | None = None
    ris_status: str = ""
    t_rel_series: list[float] = field(default_factory=list)
    rsrp_series: list[float] = field(default_factory=list)
    sinr_series: list[float] = field(default_factory=list)
    ris_angle_series: list[float] = field(default_factory=list)
    rx_angle_series: list[float] = field(default_factory=list)
    log_path: str = ""


class Controller:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.constants = Constants(
            max_ris_beam_index=cfg.beams.max_ris_index,
            beam_interval=cfg.beams.beam_interval,
            rx_angle=list(cfg.beams.rx_angles),
            window_len=cfg.beams.window_len,
            update_window=cfg.beams.update_window,
        )
        self._lock = threading.Lock()
        self.snapshot = RuntimeSnapshot()
        self._stop = threading.Event()
        self._plot_stop = threading.Event()
        self._plot_thread: threading.Thread | None = None
        self._sim_thread: threading.Thread | None = None
        self._sweep_lock = threading.Lock()

        self.mobility = False
        self.ris_beamsweep_status = False
        self.robot_stop = 1
        self.robot_dir = 1
        self.check_time = time.time()
        self.update_latency = 0.0
        self.algorithm_latency = 0.0
        self.mycounter = 1
        self.monitor = RSRPMonitor(window_len=cfg.beams.window_len)

        self.logger: ExperimentLogger | None = None
        if cfg.features.record_mobility:
            schema = "kpm" if cfg.features.mac_rsrp_tcp else "demo"
            self.logger = ExperimentLogger(
                root_dir=cfg.logging.root_dir,
                mobility_subdir=cfg.logging.mobility_subdir,
                schema=schema,
            )
            self.snapshot.log_path = str(self.logger.csv_path)
            log.info("Logging to %s", self.logger.csv_path)

        # Devices / servers (lazy-safe)
        self.xapp: XAppServer | None = None
        self.mac_client: MacRsrpTcpClient | None = None
        self.flexric: FlexricKpmLauncher | None = None
        self.xapp_monitor: LabTCPClient | None = None
        self.oai_ue: LabTCPClient | None = None
        self.gps: LabTCPClient | None = None
        self.camera: CameraTCPServer | None = None
        self.ris = RISDevice(cfg.network.ris_host, cfg.network.ris_port, enabled=cfg.features.ris)
        self.ris_rest: RISRestClient | None = None
        if cfg.features.ris_rest:
            self.ris_rest = RISRestClient(cfg.network.ris_rest_url, enabled=True)
            log.info("RIS REST control → %s", cfg.network.ris_rest_url)
        self.ue: UEEvkDevice | None = None
        self.robot: RobotDevice | None = None
        self.position: PositionDevice | None = None

        if cfg.features.mac_rsrp_tcp:
            self.mac_client = MacRsrpTcpClient(cfg.network.host, cfg.network.xapp_port)
            self.flexric = FlexricKpmLauncher(
                script=cfg.lab_ops.flexric_script,
                report_period_ms=cfg.lab_ops.kpm_report_period_ms,
                duration=cfg.lab_ops.xapp_duration,
            )
            self._set(xapp_status=f"KPM client → {cfg.network.host}:{cfg.network.xapp_port}")

        # Legacy MILCOM binary server (do NOT enable with mac_rsrp_tcp — both want :8081)
        if cfg.features.xapp_server and not cfg.features.mac_rsrp_tcp:
            self.xapp = XAppServer(cfg.network.host, cfg.network.xapp_port)
            if cfg.features.auto_start_xapp:
                self.xapp.start_server()
                self._set(xapp_status="xApp Started")

        if cfg.features.xapp_client:
            self.xapp_monitor = LabTCPClient(cfg.network.host, cfg.network.xapp_monitor_port)

        if not cfg.features.quectel:
            self.oai_ue = LabTCPClient(cfg.network.ue_laptop_host, cfg.network.ue_oai_port)

        if cfg.features.gps:
            self.gps = LabTCPClient(cfg.network.ue_laptop_host, cfg.network.gps_port)

        if cfg.features.zed_server:
            self.camera = CameraTCPServer(cfg.network.camera_host, cfg.network.camera_port)

        if cfg.features.ue_evk:
            try:
                self.ue = UEEvkDevice(
                    cfg.network.ue_evk_host,
                    rx_port=cfg.network.rpyc_rx_port,
                    tx_port=cfg.network.rpyc_tx_port,
                    enabled=True,
                    initialize=cfg.features.initialize_ue_beams,
                )
            except Exception as exc:
                log.warning("UE EVK disabled: %s", exc)
                self.ue = UEEvkDevice(cfg.network.ue_evk_host, enabled=False)

        if cfg.features.robot_redis:
            try:
                self.robot = RobotDevice(
                    cfg.network.ue_evk_host, port=cfg.network.redis_port, enabled=True
                )
            except Exception as exc:
                log.warning("Robot disabled: %s", exc)

        if cfg.features.marvelmind:
            try:
                self.position = PositionDevice(
                    tty=cfg.devices.marvelmind_tty,
                    baud=cfg.devices.marvelmind_baud,
                    enabled=True,
                )
            except Exception as exc:
                log.warning("Marvelmind disabled: %s", exc)

        if cfg.features.ris:
            try:
                self.ris.set_beam(160, cmd="RIS")
            except Exception as exc:
                log.warning("Initial RIS set failed: %s", exc)

    # ---- snapshot helpers ----
    def _set(self, **kwargs) -> None:
        with self._lock:
            for key, value in kwargs.items():
                setattr(self.snapshot, key, value)

    def get_snapshot(self) -> RuntimeSnapshot:
        with self._lock:
            s = self.snapshot
            mac_ok = bool(self.mac_client and self.mac_client.connected)
            return RuntimeSnapshot(
                status=s.status,
                monitor_msg=s.monitor_msg,
                bs_status=s.bs_status,
                xapp_status=s.xapp_status,
                oai_status=s.oai_status,
                mobility_active=s.mobility_active,
                plotting=s.plotting,
                mac_connected=mac_ok,
                current_rsrp=s.current_rsrp,
                current_sinr=s.current_sinr,
                ran_ue_id=s.ran_ue_id,
                current_ris_beam=s.current_ris_beam,
                current_rx_index=s.current_rx_index,
                ris_status=s.ris_status,
                t_rel_series=list(s.t_rel_series),
                rsrp_series=list(s.rsrp_series),
                sinr_series=list(s.sinr_series),
                ris_angle_series=list(s.ris_angle_series),
                rx_angle_series=list(s.rx_angle_series),
                log_path=s.log_path,
            )

    def _append_series(self, rsrp: float, ris_idx: int, rx_idx: int) -> None:
        ris_ang, rx_ang = index_to_angles(
            int(ris_idx),
            int(rx_idx),
            max_ris_index=self.constants.max_ris_beam_index,
            rx_angles=self.constants.rx_angle,
        )
        with self._lock:
            self.snapshot.current_rsrp = float(rsrp)
            self.snapshot.current_ris_beam = int(ris_idx)
            self.snapshot.current_rx_index = int(rx_idx)
            self.snapshot.rsrp_series.append(float(rsrp))
            self.snapshot.ris_angle_series.append(float(ris_ang))
            self.snapshot.rx_angle_series.append(float(rx_ang))
            max_n = self.constants.update_window
            if len(self.snapshot.rsrp_series) > max_n:
                self.snapshot.rsrp_series = self.snapshot.rsrp_series[-max_n:]
                self.snapshot.ris_angle_series = self.snapshot.ris_angle_series[-max_n:]
                self.snapshot.rx_angle_series = self.snapshot.rx_angle_series[-max_n:]

    def _append_mac_sample(self, sample: MacKpiSample) -> None:
        max_n = int(self.cfg.plot.max_points)
        with self._lock:
            self.snapshot.current_rsrp = float(sample.rsrp)
            self.snapshot.current_sinr = float(sample.sinr)
            self.snapshot.ran_ue_id = int(sample.ran_ue)
            self.snapshot.t_rel_series.append(float(sample.t_rel_s))
            self.snapshot.rsrp_series.append(float(sample.rsrp))
            self.snapshot.sinr_series.append(float(sample.sinr))
            if len(self.snapshot.rsrp_series) > max_n:
                self.snapshot.t_rel_series = self.snapshot.t_rel_series[-max_n:]
                self.snapshot.rsrp_series = self.snapshot.rsrp_series[-max_n:]
                self.snapshot.sinr_series = self.snapshot.sinr_series[-max_n:]

    # ---- lifecycle ----
    def start_background_workers(self) -> None:
        self._stop.clear()
        if self.cfg.features.simulate_rsrp and not self.cfg.features.mac_rsrp_tcp:
            self._sim_thread = threading.Thread(target=self._sim_kpi_loop, daemon=True)
            self._sim_thread.start()
            log.info("Offline KPI simulator running")
        if self.cfg.features.mac_rsrp_tcp and self.cfg.features.auto_connect_mac_rsrp:
            self.start_plotting()

    def stop_background_workers(self) -> None:
        self.stop_plotting()
        self._stop.set()
        if self.mac_client:
            self.mac_client.stop()
        if self.xapp:
            self.xapp.stop_server()
        if self.camera:
            self.camera.stop_server()
        if self.ue:
            self.ue.close()
        if self.position:
            self.position.stop()
        if self._sim_thread:
            self._sim_thread.join(timeout=2)
        if self.logger:
            self.logger.close()

    def _kpi_queue(self) -> queue.Queue | None:
        if self.mac_client is not None:
            return self.mac_client.data_queue
        if self.xapp is not None:
            return self.xapp.data_queue
        return None

    def _sim_kpi_loop(self) -> None:
        """Feed fake KPIs into an in-memory xApp-compatible queue."""
        if self.xapp is None:
            self.xapp = XAppServer(self.cfg.network.host, self.cfg.network.xapp_port)
        t0 = time.time()
        while not self._stop.is_set():
            rsrp = -75.0 + 8.0 * random.random() + 2.0 * ((time.time() - t0) % 5)
            self.xapp.KPIs = [rsrp, 10.0, 2.0]
            self.xapp.data_queue.put(list(self.xapp.KPIs))
            if self.xapp.data_queue.full():
                self.xapp.data_queue.queue.clear()
            time.sleep(0.25)

    # ---- GUI-facing controls ----
    def start_kpm_xapp(self) -> str:
        if not self.flexric:
            return "KPM launcher not configured (enable mac_rsrp_tcp)"
        msg = self.flexric.start()
        self._set(xapp_status=msg)
        return msg

    def stop_kpm_xapp(self) -> str:
        if not self.flexric:
            return "KPM launcher not configured (enable mac_rsrp_tcp)"
        msg = self.flexric.stop()
        self._set(xapp_status=msg)
        return msg

    def status_kpm_xapp(self) -> str:
        if not self.flexric:
            return "KPM launcher not configured (enable mac_rsrp_tcp)"
        msg = self.flexric.status()
        self._set(xapp_status=msg[:200])
        return msg

    def start_xapp_server(self) -> str:
        if self.cfg.features.mac_rsrp_tcp:
            return self.start_kpm_xapp()
        if not self.xapp:
            return "xApp server not configured"
        self.xapp.start_server()
        self._set(xapp_status="xApp Started")
        return "xApp Started"

    def stop_xapp_server(self) -> str:
        if self.cfg.features.mac_rsrp_tcp:
            return self.stop_kpm_xapp()
        if not self.xapp:
            return "xApp server not configured"
        self.xapp.stop_server()
        self._set(xapp_status="xApp Stopped")
        return "xApp Stopped"

    def start_xapp_monitor(self) -> str:
        if not self.xapp_monitor:
            return "xApp client not configured"
        status = self.xapp_monitor.send_oai_ue_ACK("START", 0)
        self._set(xapp_status=f"Monitor: {status}")
        return str(status)

    def stop_xapp_monitor(self) -> str:
        if not self.xapp_monitor:
            return "xApp client not configured"
        status = self.xapp_monitor.send_oai_ue_ACK("STOP", 0)
        self._set(xapp_status=f"Monitor: {status}")
        return str(status)

    def exit_xapp_monitor(self) -> str:
        if not self.xapp_monitor:
            return "xApp client not configured"
        status = self.xapp_monitor.send_oai_ue_ACK("EXIT", 0)
        self._set(xapp_status=f"Monitor: {status}")
        return str(status)

    def start_ue_session(self) -> str:
        if not self.oai_ue:
            return "OAI UE client not configured"
        status = self.oai_ue.send_oai_ue_ACK("START", 0)
        self._set(oai_status=str(status))
        return str(status)

    def stop_ue_session(self) -> str:
        if not self.oai_ue:
            return "OAI UE client not configured"
        status = self.oai_ue.send_oai_ue_ACK("STOP", 0)
        self._set(oai_status=str(status))
        return str(status)

    def exit_ue_session(self) -> str:
        if not self.oai_ue:
            return "OAI UE client not configured"
        status = self.oai_ue.send_oai_ue_ACK("EXIT", 0)
        self._set(oai_status=str(status))
        return str(status)

    def get_ue_ip(self) -> str:
        if not self.oai_ue:
            return "OAI UE client not configured"
        status = self.oai_ue.send_oai_ue_ACK("IP", 0)
        self._set(oai_status=str(status))
        return str(status)

    def update_ue_ip(self) -> str:
        if not self.oai_ue:
            return "OAI UE client not configured"
        status = self.oai_ue.send_oai_ue_ACK("NET", 0)
        self._set(oai_status=str(status))
        return str(status)

    def set_mobility(self, active: bool) -> None:
        self.mobility = active
        self._set(mobility_active=active, monitor_msg="Mobility Active" if active else "Mobility Off")
        if not active and self.robot:
            self.robot.stop(direction=self.robot_dir)

    def set_beamsweep(self, active: bool) -> None:
        self.ris_beamsweep_status = active
        self._set(bs_status="Beam sweep ON" if active else "Beam sweep OFF")

    def set_robot_inputs(self, direction: int, stop: int) -> None:
        self.robot_dir = int(direction)
        self.robot_stop = int(stop)

    def move_robot(self) -> str:
        if self.robot:
            moving = self.robot_stop == 0
            key = 0.4 if moving else 0.1
            self.robot.push(status=moving, key=key, direction=self.robot_dir)
            return f"dir={self.robot_dir} stop={self.robot_stop}"
        return "Robot not configured"

    def reset_robot(self) -> str:
        self.robot_stop = 0
        if self.robot:
            self.robot.pulse_reset()
        return "Reset"

    def set_ris_beam(self, index: int) -> int:
        index = int(index)
        try:
            if self.ris_rest is not None:
                beam = self.ris_rest.set_beam(index)
                status = self.ris_rest.last_status
            elif self.cfg.features.ris:
                beam = self.ris.set_beam(index, cmd="SET")
                status = f"TCP SET → {beam}"
            else:
                beam = index
                status = "local only (ris/ris_rest disabled)"
            self._set(current_ris_beam=beam, status=f"RIS={beam}", ris_status=status)
            return beam
        except Exception as exc:
            self._set(ris_status=str(exc), status=f"RIS apply failed: {exc}")
            raise

    def set_ue_beam(self, index: int) -> int:
        if self.ue is None:
            self._set(current_rx_index=int(index), status=f"RX={index} (sim)")
            return int(index)
        beam = self.ue.set_beam(int(index))
        self._set(current_rx_index=beam, status=f"RX={beam}")
        return beam

    def clear_series(self) -> None:
        with self._lock:
            self.snapshot.rsrp_series.clear()
            self.snapshot.sinr_series.clear()
            self.snapshot.t_rel_series.clear()
            self.snapshot.ris_angle_series.clear()
            self.snapshot.rx_angle_series.clear()
        self.monitor.reset()
        self.constants.counter = -1

    def start_plotting(self) -> None:
        if self._plot_thread and self._plot_thread.is_alive():
            return
        if self.cfg.features.mac_rsrp_tcp:
            if self.mac_client is None:
                self.mac_client = MacRsrpTcpClient(
                    self.cfg.network.host, self.cfg.network.xapp_port
                )
            self.mac_client.start()
            self._plot_stop.clear()
            self._set(
                plotting=True,
                status=f"MAC RSRP ← {self.cfg.network.host}:{self.cfg.network.xapp_port}",
            )
            self._plot_thread = threading.Thread(target=self._mac_receive_loop, daemon=True)
            self._plot_thread.start()
            return

        if self._kpi_queue() is None and not self.cfg.features.simulate_rsrp:
            self._set(status="No KPI source (enable xapp_server, mac_rsrp_tcp, or simulate_rsrp)")
            return
        self._plot_stop.clear()
        self._set(plotting=True, status="Plotting RSRP")
        self._plot_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._plot_thread.start()

    def stop_plotting(self) -> None:
        self._plot_stop.set()
        self._set(plotting=False, status="Plotting stopped")
        if self.mac_client and self.cfg.features.mac_rsrp_tcp:
            # keep process alive but stop reader when leaving plot mode? reconnect is fine —
            # stop client so we don't fill queue forever
            self.mac_client.stop()
        if self._plot_thread:
            self._plot_thread.join(timeout=2)
            self._plot_thread = None

    def _mac_receive_loop(self) -> None:
        assert self.mac_client is not None
        q = self.mac_client.data_queue
        while not self._plot_stop.is_set() and not self._stop.is_set():
            try:
                sample = q.get(timeout=0.5)
            except Exception:
                continue
            if not isinstance(sample, MacKpiSample):
                continue
            start = datetime.now().timestamp()
            self._append_mac_sample(sample)
            status = "connected" if self.mac_client.connected else "waiting for xApp…"
            self._set(
                monitor_msg=f"ran_ue_id={sample.ran_ue}  [{status}]",
                xapp_status=status,
            )
            if self.cfg.features.record_mobility and self.logger:
                self.logger.log_kpm_row(
                    timestamp=start,
                    t_rel_s=sample.t_rel_s,
                    ran_ue_id=sample.ran_ue,
                    rsrp=sample.rsrp,
                    sinr=sample.sinr,
                    update_latency=datetime.now().timestamp() - start,
                )
            if self.mobility and sample.rsrp == sample.rsrp:  # not NaN
                self.monitor.push(sample.rsrp)
                dropped, _ = self.monitor.evaluate(threshold=1.0)
                if dropped:
                    self._set(monitor_msg=f"RSRP Dropped  ran_ue={sample.ran_ue}")

    # ---- main KPI loop (legacy receive_rsrp_data, no GUI) ----
    def _ensure_beam_state(self) -> None:
        with self._lock:
            ris = self.snapshot.current_ris_beam
            rx = self.snapshot.current_rx_index
        if ris is None:
            ris = self.ris.get_beam() if self.cfg.features.ris else 0
            self._set(current_ris_beam=int(ris))
        if rx is None:
            if self.ue and self.ue.enabled:
                rx = self.ue.get_beam()
            else:
                rx = 5
            self._set(current_rx_index=int(rx))

    def _receive_loop(self) -> None:
        q = self._kpi_queue()
        if q is None:
            self._set(status="No KPI queue")
            return
        while not self._plot_stop.is_set() and not self._stop.is_set():
            if self.constants.counter + 1 == self.constants.update_window:
                self.constants.run_term += 1
                self.monitor.reset()
                self.constants.counter = -1
                self.clear_series()

            try:
                start = datetime.now().timestamp()
                data = q.get(timeout=0.5)
            except Exception:
                continue

            try:
                current_rsrp = float(data[0])
                dl = float(data[1]) if len(data) > 1 and data[1] is not None else 0.0
                ul = float(data[2]) if len(data) > 2 and data[2] is not None else 0.0
                self._ensure_beam_state()
                snap = self.get_snapshot()
                ris_beam = int(snap.current_ris_beam or 0)
                rx_idx = int(snap.current_rx_index or 5)

                if current_rsrp == 0:
                    if self.constants.counter == -1:
                        self.constants.counter = 180
                    self.constants.counter += 1
                    if self.ris_beamsweep_status:
                        send_index = (self.constants.counter + 1) % self.constants.max_ris_beam_index
                        ris_beam = self.ris.set_beam(send_index, cmd="RIS")
                        if self.ue and self.ue.enabled:
                            best_rx, best_val = rx_idx, -999.0
                            for cand in range(5, 7):
                                self.ue.set_beam(cand)
                                try:
                                    sample = q.get(timeout=0.2)[0]
                                except Exception:
                                    sample = 0
                                if sample > best_val:
                                    best_val, best_rx = sample, cand
                            rx_idx = self.ue.set_beam(best_rx)
                            current_rsrp = float(best_val)
                        self._append_series(current_rsrp, ris_beam, rx_idx)
                        self._set(
                            monitor_msg="UE Not Connected, RIS Beam Search",
                            bs_status=f"Searching {send_index}",
                        )
                    else:
                        self._set(monitor_msg="UE Not Connected")
                    continue

                # Connected UE path
                self.ris_beamsweep_status = False
                self.check_time = time.time()
                self.constants.counter += 1
                self.monitor.push(current_rsrp)
                self._append_series(current_rsrp, ris_beam, rx_idx)
                if not self.mobility:
                    self._set(monitor_msg="UE is running", bs_status=" ")

                if self.cfg.features.record_mobility and self.logger:
                    ris_ang, rx_ang = index_to_angles(
                        ris_beam,
                        rx_idx,
                        max_ris_index=self.constants.max_ris_beam_index,
                        rx_angles=self.constants.rx_angle,
                    )
                    self.logger.log_row(
                        timestamp=datetime.now().timestamp(),
                        update_latency=self.update_latency,
                        rsrp=current_rsrp,
                        ris_index=ris_beam,
                        rx_index=rx_idx,
                        ris_angle=ris_ang,
                        rx_angle=rx_ang,
                    )

                if self.mobility:
                    dropped, _ = self.monitor.evaluate(threshold=1.0)
                    self._set(monitor_msg="RSRP Dropped" if dropped else "RSRP Stable")
                    do_reopt = dropped and self.cfg.features.mobility_reopt
                    t0 = time.time()
                    if do_reopt:
                        self.joint_bs_ris_with_mobility(ris_beam, rx_idx)
                        self.mycounter += 1
                        self._set(status="Algorithm Applied")
                    else:
                        time.sleep(0.05)
                    self.algorithm_latency = time.time() - t0
                    if self.robot:
                        moving = self.robot_stop == 0
                        tt_now = min(time.time() - self.check_time, 1.5)
                        self.robot.push(
                            status=moving, key=tt_now if moving else tt_now, direction=self.robot_dir
                        )

                self.update_latency = datetime.now().timestamp() - start
            except Exception:
                log.exception("Error in RSRP receive loop")

    def record_nonzero_kpi_data(self, num_capture: int = 1):
        q = self._kpi_queue()
        rsrps, dl, ul = [], [], []
        checks = 0
        while len(rsrps) < num_capture and checks < 5:
            checks += 1
            if q is None:
                break
            try:
                retrieved = q.get(timeout=0.2)
            except Exception:
                break
            data, dlt, ult = retrieved[0], retrieved[1], retrieved[2]
            rsrps.append(float(data) if data else 0.0)
            dl.append(float(dlt) if dlt else 0.0)
            ul.append(float(ult) if ult else 0.0)
        return np.array(rsrps), np.array(dl), np.array(ul)

    def joint_bs_ris_with_mobility(self, current_ris_index: int, current_rx_index: int) -> dict:
        optimizer = BeamIndexOptimizer2(
            max_ris_index=self.constants.max_ris_beam_index,
            max_rx_index=10,
            current_ris_index=current_ris_index,
            current_rx_index=current_rx_index,
            num_index_interval=4,
        )
        range_beams = optimizer.get_ris_beam_index_range()
        selected_rx = optimizer.get_rx_beam_index_range()
        t0 = time.time()
        ris_rsrp = np.zeros(len(range_beams))
        ris_dl = np.zeros(len(range_beams))
        ris_ul = np.zeros(len(range_beams))
        for kk, ris_index in enumerate(range_beams):
            self.ris.set_beam(int(ris_index), cmd="RIS")
            xapp_record = self.record_nonzero_kpi_data(num_capture=1)
            ris_rsrp[kk] = float(np.mean(xapp_record[0])) if xapp_record[0].size else -999.0
            ris_dl[kk] = float(np.mean(xapp_record[1])) if xapp_record[1].size else 0.0
            ris_ul[kk] = float(np.mean(xapp_record[2])) if xapp_record[2].size else 0.0
            self._append_series(ris_rsrp[kk], int(ris_index), current_rx_index)

        optimal = int(range_beams[int(np.argmax(ris_rsrp))])
        self.ris.set_beam(optimal, cmd="SET")
        self.constants.latency = time.time() - t0

        if self.mycounter % 50 == 0 and self.ue and self.ue.enabled:
            rx_rsrp = np.zeros(len(selected_rx))
            for i, rx_index in enumerate(selected_rx):
                self.ue.set_beam(int(rx_index))
                time.sleep(0.2)
                rec = self.record_nonzero_kpi_data(1)
                rx_rsrp[i] = float(np.mean(rec[0])) if rec[0].size else -999.0
            current_rx_index = int(selected_rx[int(np.argmax(rx_rsrp))])
            self.ue.set_beam(current_rx_index)

        self._set(current_ris_beam=optimal, current_rx_index=current_rx_index, bs_status="Re-opt done")
        return {
            "RSRP": ris_rsrp,
            "DLTH": ris_dl,
            "ULTH": ris_ul,
            "latency": self.constants.latency,
            "RIS_index": optimal,
            "RX_index": current_rx_index,
        }

    def joint_beamsweeping(self) -> dict:
        """Coarse joint RIS×RX search (legacy Joint BS button)."""
        self._set(bs_status="Joint BS running")
        self._ensure_beam_state()
        snap = self.get_snapshot()
        range_beams = np.arange(
            0,
            int(self.constants.max_ris_beam_index) - 2,
            int(self.constants.beam_interval),
        )
        selected_rx = np.array([snap.current_rx_index or 5])
        matrix = np.zeros((len(selected_rx), len(range_beams)))
        for ri, rx in enumerate(selected_rx):
            if self.ue and self.ue.enabled:
                self.ue.set_beam(int(rx))
            for ki, ris in enumerate(range_beams):
                self.ris.set_beam(int(ris), cmd="RIS")
                rec = self.record_nonzero_kpi_data(1)
                val = float(np.mean(rec[0])) if rec[0].size else 0.0
                matrix[ri, ki] = val
                self._append_series(val, int(ris), int(rx))
                if val == 0.0 and not self.cfg.features.simulate_rsrp:
                    break
        best_rx_i = int(np.argmax(np.max(matrix, axis=1)))
        best_ris_i = int(np.argmax(matrix[best_rx_i, :]))
        best_rx = int(selected_rx[best_rx_i])
        best_ris = int(range_beams[best_ris_i])
        if self.ue and self.ue.enabled:
            self.ue.set_beam(best_rx)
        self.ris.set_beam(best_ris, cmd="SET")
        self._set(bs_status="Beam Search Done!", current_ris_beam=best_ris, current_rx_index=best_rx)
        return {"optimal_ris_index": best_ris, "optimal_rx_index": best_rx, "RSRP": matrix}

    def start_beam_sweep(self) -> None:
        """Neighborhood sweep used by the Phase-1 offline button."""
        if self._sweep_lock.locked():
            return
        threading.Thread(target=self._beam_sweep_worker, daemon=True).start()

    def stop_beam_sweep(self) -> None:
        self._set(status="Sweep stop requested")

    def _beam_sweep_worker(self) -> None:
        with self._sweep_lock:
            self._set(status="Sweeping")
            self._ensure_beam_state()
            snap = self.get_snapshot()
            optimizer = BeamIndexOptimizer(
                max_ris_index=self.constants.max_ris_beam_index,
                max_rx_index=max(1, len(self.constants.rx_angle) - 1),
                current_ris_index=int(snap.current_ris_beam or 0),
                current_rx_index=int(snap.current_rx_index or 3),
                num_index_interval=3,
            )

            def measure(beam):
                self.ris.set_beam(int(beam), cmd="RIS")
                rec = self.record_nonzero_kpi_data(1)
                val = float(np.mean(rec[0])) if rec[0].size else self.latest_rsrp(0.2)
                self._append_series(val, int(beam), int(snap.current_rx_index or 3))
                return val

            best, results = BeamSearch(optimizer).sweep(measure)
            self.ris.set_beam(best, cmd="SET")
            self._set(status=f"Best RIS beam: {best}", current_ris_beam=best)
            log.info("Beam sweep done: best=%s", best)

    def latest_rsrp(self, timeout: float = 0.5) -> float:
        q = self._kpi_queue()
        if q is None:
            return -999.0
        try:
            item = q.get(timeout=timeout)
        except Exception:
            return -999.0
        if isinstance(item, MacKpiSample):
            return float(item.rsrp) if item.rsrp == item.rsrp else -999.0
        try:
            return float(item[0])
        except Exception:
            return -999.0

    # aliases used by older GUI scaffold
    @property
    def status(self) -> str:
        return self.get_snapshot().status

    @property
    def data_q(self):
        return self._kpi_queue() or queue.Queue()
