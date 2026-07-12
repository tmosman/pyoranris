"""RIS beam control via REST API.

Example:
  POST http://localhost:8080/api/beam/apply
  Content-Type: application/json
  {"index": 1}
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

log = logging.getLogger(__name__)


class RISRestClient:
    def __init__(
        self,
        apply_url: str = "http://localhost:8080/api/beam/apply",
        *,
        timeout: float = 3.0,
        enabled: bool = True,
    ):
        self.apply_url = apply_url.rstrip("/")
        self.timeout = timeout
        self.enabled = enabled
        self.last_beam: int | None = None
        self.last_status: str = ""
        self.last_response: str = ""

    def set_beam(self, index: int) -> int:
        index = int(index)
        if not self.enabled:
            self.last_beam = index
            self.last_status = "disabled (local only)"
            return index

        payload = json.dumps({"index": index}).encode("utf-8")
        req = urllib.request.Request(
            self.apply_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                self.last_response = body
                self.last_beam = index
                self.last_status = f"OK HTTP {resp.status}"
                log.info("RIS REST apply index=%s → %s", index, self.last_status)
                return index
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            self.last_response = body
            self.last_status = f"HTTP {exc.code}: {body[:120]}"
            log.error("RIS REST apply failed: %s", self.last_status)
            raise RuntimeError(self.last_status) from exc
        except Exception as exc:
            self.last_status = f"error: {exc}"
            log.error("RIS REST apply failed: %s", exc)
            raise
