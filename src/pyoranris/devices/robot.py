"""Redis-backed robot motion commands (optional)."""

from __future__ import annotations

import json
import logging

log = logging.getLogger(__name__)


class RobotDevice:
    def __init__(
        self,
        host: str,
        port: int = 6379,
        enabled: bool = False,
        queue_name: str = "queue_name",
    ):
        self.enabled = enabled
        self.queue_name = queue_name
        self._client = None
        if enabled:
            try:
                import redis
            except ImportError as exc:
                raise RuntimeError(
                    "redis is required for robot control. pip install redis"
                ) from exc
            self._client = redis.Redis(host=host, port=port)
            log.info("Robot redis client -> %s:%s", host, port)

    def push(self, *, status: bool, key: float, direction: str | int = 1) -> None:
        if not self.enabled or self._client is None:
            return
        payload = {"status": status, "key": float(key), "dir": str(direction)}
        self._client.lpush(self.queue_name, json.dumps(payload))

    def pulse_reset(self) -> None:
        if not self.enabled or self._client is None:
            return
        self._client.lpush(self.queue_name, json.dumps({"status": True, "key": 0.1}))
        try:
            self._client.brpop(self.queue_name, timeout=1)
        except Exception:
            pass

    def stop(self, direction: int = 1) -> None:
        self.push(status=False, key=0.1, direction=direction)
