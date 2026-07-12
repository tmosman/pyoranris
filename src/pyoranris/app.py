"""Application entry used by CLI and `python -m pyoranris`."""

from __future__ import annotations

import logging

from pyoranris.config import AppConfig, describe_features, load_config
from pyoranris.controllers.controller import Controller
from pyoranris.utils.logging_setup import setup_logging

log = logging.getLogger(__name__)


def run(cfg: AppConfig, *, with_gui: bool = True) -> int:
    for line in describe_features(cfg):
        log.info(line)

    ctrl = Controller(cfg)
    ctrl.start_background_workers()
    try:
        if with_gui:
            from pyoranris.gui.dpg_gui import DearPyGuiApp

            DearPyGuiApp(controller=ctrl).run()
        else:
            log.info("Headless mode — Ctrl+C to stop")
            import time

            while True:
                rsrp = ctrl.latest_rsrp(timeout=1.0)
                if rsrp > -900:
                    log.info("RSRP=%.2f", rsrp)
                time.sleep(0.5)
    except KeyboardInterrupt:
        log.info("Interrupted")
    finally:
        ctrl.stop_background_workers()
    return 0


def main(config_path: str | None = None, *, with_gui: bool = True) -> int:
    setup_logging()
    cfg = load_config(config_path)
    return run(cfg, with_gui=with_gui)


if __name__ == "__main__":
    raise SystemExit(main())
