"""CLI: pyoranris run|show-config|legacy-info"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyoranris import __version__
from pyoranris.app import main as app_main
from pyoranris.config import describe_features, load_config
from pyoranris.utils.logging_setup import setup_logging


def _cmd_run(args: argparse.Namespace) -> int:
    return app_main(args.config, with_gui=not args.headless)


def _cmd_show_config(args: argparse.Namespace) -> int:
    setup_logging()
    cfg = load_config(args.config)
    print("\n".join(describe_features(cfg)))
    print(f"network.host={cfg.network.host}")
    print(f"network.ris_host={cfg.network.ris_host}:{cfg.network.ris_port}")
    print(f"network.ue_evk_host={cfg.network.ue_evk_host}:{cfg.network.ue_evk_port}")
    print(f"logging.root_dir={cfg.logging.root_dir}")
    return 0


def _cmd_legacy_info(_: argparse.Namespace) -> int:
    root = Path(__file__).resolve().parents[2]
    legacy = root / "legacy"
    print(f"pyoranris {__version__}")
    print(f"Legacy freeze directory: {legacy}")
    if legacy.exists():
        for path in sorted(legacy.iterdir()):
            print(f"  - {path.name}")
    print("See docs/GOLDEN_PATH.md and docs/MIGRATION.md")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyoranris",
        description="Transferable O-RAN + RIS indoor demo toolkit",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Start controller (+ GUI by default)")
    run_p.add_argument(
        "--config",
        "-c",
        default="configs/offline_sim.yaml",
        help="Path to YAML profile (default: configs/offline_sim.yaml)",
    )
    run_p.add_argument(
        "--headless",
        action="store_true",
        help="Run without DearPyGui (log RSRP to console)",
    )
    run_p.set_defaults(func=_cmd_run)

    show_p = sub.add_parser("show-config", help="Print resolved feature flags / hosts")
    show_p.add_argument("--config", "-c", default="configs/offline_sim.yaml")
    show_p.set_defaults(func=_cmd_show_config)

    leg_p = sub.add_parser("legacy-info", help="Show Phase-0 frozen sources")
    leg_p.set_defaults(func=_cmd_legacy_info)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main(sys.argv[1:])
