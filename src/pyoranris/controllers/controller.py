"""Orchestration layer — no DearPyGui imports in the hot path."""

from __future__ import annotations

import logging
import queue
import random
import threading
import time

from pyoranris.algorithms.beam_optimizer import BeamIndexOptimizer, BeamSearch
from pyoranris.config import AppConfig
from pyoranris.data.experiment_logger import ExperimentLogger
from pyoranris.models.constants import Constants
from pyoranris.net.rsrp_server import SimpleTCPServer

log = logging.getLogger(__name__)


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
        self.data_q: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self.worker_thread: threading.Thread | None = None
        self._sweep_lock = threading.Lock()
        self._history: list[tuple[int, float]] = []
        self.status = "Idle"
        self.logger: ExperimentLogger | None = None
        self.rsrp_server: SimpleTCPServer | None = None

        if cfg.features.record_mobility:
            self.logger = ExperimentLogger(
                root_dir=cfg.logging.root_dir,
                mobility_subdir=cfg.logging.mobility_subdir,
            )
            log.info("Logging to %s", self.logger.csv_path)

        if not cfg.features.simulate_rsrp:
            self.rsrp_server = SimpleTCPServer(
                host=cfg.network.host if cfg.network.host != "127.0.0.1" else "0.0.0.0",
                port=cfg.network.rsrp_port,
            )

    def start_background_workers(self) -> None:
        self._stop.clear()
        if self.rsrp_server:
            self.rsrp_server.start_server()
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
        elif self.cfg.features.simulate_rsrp:
            self.worker_thread = threading.Thread(target=self._sim_loop, daemon=True)
            self.worker_thread.start()
            log.info("Offline RSRP simulator running")

    def _worker_loop(self) -> None:
        assert self.rsrp_server is not None
        while not self._stop.is_set():
            try:
                vals = self.rsrp_server.data_queue.get(timeout=0.5)
                self.data_q.put(vals)
            except Exception:
                pass

    def _sim_loop(self) -> None:
        t0 = time.time()
        while not self._stop.is_set():
            # Mildly varying fake RSRP for GUI / sweep demos
            rsrp = -75.0 + 8.0 * random.random() + 2.0 * ((time.time() - t0) % 5)
            self.data_q.put((rsrp, 0.0, 0.0))
            time.sleep(0.25)

    def stop_background_workers(self) -> None:
        self._stop.set()
        if self.rsrp_server:
            self.rsrp_server.stop_server()
        if self.worker_thread:
            self.worker_thread.join(timeout=2)
        if self.logger:
            self.logger.close()

    def latest_rsrp(self, timeout: float = 0.5) -> float:
        try:
            vals = self.data_q.get(timeout=timeout)
            return float(vals[0])
        except Exception:
            return -999.0

    def start_beam_sweep(self) -> None:
        if self._sweep_lock.locked():
            log.info("sweep already running")
            return
        threading.Thread(target=self._beam_sweep_worker, daemon=True).start()

    def stop_beam_sweep(self) -> None:
        self.status = "Sweep stop requested"
        log.info(self.status)

    def _beam_sweep_worker(self) -> None:
        with self._sweep_lock:
            self.status = "Sweeping"
            optimizer = BeamIndexOptimizer(
                max_ris_index=self.constants.max_ris_beam_index,
                max_rx_index=max(1, len(self.constants.rx_angle) - 1),
                current_ris_index=max(0, self.constants.counter),
                current_rx_index=3,
                num_index_interval=3,
            )
            best, results = BeamSearch(optimizer).sweep(
                self.latest_rsrp, update_state_fn=self._update_on_measure
            )
            self.status = f"Best RIS beam: {best}"
            log.info("Beam sweep done: best=%s results=%s", best, results)
            if self.logger:
                self.logger.log_row(
                    timestamp=time.time(),
                    update_latency=0.0,
                    rsrp=results.get(best, -999.0),
                    ris_index=best,
                    rx_index=3,
                    ris_angle=0.0,
                    rx_angle=self.constants.rx_angle[3]
                    if len(self.constants.rx_angle) > 3
                    else 0.0,
                )

    def _update_on_measure(self, beam, rsrp) -> None:
        self._history.append((int(beam), float(rsrp)))
        self._history = self._history[-200:]
        self.status = f"Measuring beam {beam}: {rsrp:.1f} dBm"
