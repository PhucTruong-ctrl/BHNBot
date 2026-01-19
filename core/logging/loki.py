"""Loki log handler for pushing structured logs to Grafana Loki."""

import json
import logging
import os
import time
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError


class LokiHandler(logging.Handler):
    """Push logs to Grafana Loki via HTTP Push API."""
    
    def __init__(
        self,
        url: Optional[str] = None,
        labels: Optional[dict[str, str]] = None,
        batch_size: int = 100,
        flush_interval: float = 5.0,
    ):
        super().__init__()
        base_url = url or os.getenv("LOKI_URL", "http://localhost:3100")
        if not base_url.endswith("/loki/api/v1/push"):
            base_url = base_url.rstrip("/") + "/loki/api/v1/push"
        self.url = base_url
        self.labels = labels or {"service": "bhnbot", "env": os.getenv("ENVIRONMENT", "dev")}
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._buffer: list[tuple[int, str]] = []
        self._last_flush = time.time()
    
    def emit(self, record: logging.LogRecord) -> None:
        try:
            timestamp_ns = int(record.created * 1e9)
            message = self.format(record)
            self._buffer.append((timestamp_ns, message))
            
            should_flush = (
                len(self._buffer) >= self.batch_size
                or time.time() - self._last_flush >= self.flush_interval
            )
            
            if should_flush:
                self._flush()
                
        except Exception:
            self.handleError(record)
    
    def _flush(self) -> None:
        if not self._buffer:
            return
        
        values = [[str(ts), msg] for ts, msg in self._buffer]
        self._buffer.clear()
        self._last_flush = time.time()
        
        payload = {
            "streams": [
                {
                    "stream": self.labels,
                    "values": values,
                }
            ]
        }
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = Request(
                self.url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=5) as response:
                response.read()
        except URLError:
            pass
    
    def close(self) -> None:
        self._flush()
        super().close()


def attach_loki_handler(
    loki_url: Optional[str] = None,
    labels: Optional[dict[str, str]] = None,
) -> Optional[LokiHandler]:
    """Attach Loki handler to root logger if LOKI_URL is configured."""
    url = loki_url or os.getenv("LOKI_URL")
    if not url:
        return None
    
    handler = LokiHandler(url=url, labels=labels)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(handler)
    return handler
