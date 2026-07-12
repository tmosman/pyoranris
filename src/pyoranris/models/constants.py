from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Constants:
    """Runtime constants formerly in classes_file.CONSTANTS."""

    cap_len: int = 1
    update_window: int = 1001
    counter: int = -1
    check_begin: int | None = None
    data_counter: int = -1
    run_term: int = 1
    window_len: int = 5
    current_rsrp: float = 0.0
    detect_rsrp: float = 0.0
    max_ris_beam_index: int = 182
    beam_interval: int = 1
    latency: float = 0.0
    rx_angle: list[float] = field(
        default_factory=lambda: [-27, -21, -15, -9, -3, 0, 3, 9, 15, 21, 27]
    )


# Back-compat alias used by earlier stubs
CONSTANTS = Constants
