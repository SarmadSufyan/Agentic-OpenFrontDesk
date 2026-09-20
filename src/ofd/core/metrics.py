"""Tiny in-process metrics registry, rendered in Prometheus text format at /metrics.

Dependency-free (no prometheus_client) to keep the image lean. Counters are per-process; with multiple
API replicas a real scraper aggregates across them. See docs/14-observability.md.
"""

from __future__ import annotations

import threading
import time

from ofd import __version__

_start = time.time()
_lock = threading.Lock()
_counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = {}


def incr(name: str, **labels: str) -> None:
    key = (name, tuple(sorted(labels.items())))
    with _lock:
        _counters[key] = _counters.get(key, 0) + 1


def render() -> str:
    lines = [
        "# HELP ofd_info Build info",
        "# TYPE ofd_info gauge",
        f'ofd_info{{version="{__version__}"}} 1',
        "# HELP ofd_uptime_seconds Seconds since process start",
        "# TYPE ofd_uptime_seconds gauge",
        f"ofd_uptime_seconds {time.time() - _start:.0f}",
        "# HELP ofd_http_requests_total HTTP requests handled",
        "# TYPE ofd_http_requests_total counter",
    ]
    with _lock:
        items = sorted(_counters.items())
    for (name, labels), val in items:
        if name != "http_requests_total":
            continue
        lbl = ",".join(f'{k}="{v}"' for k, v in labels)
        lines.append(f"ofd_http_requests_total{{{lbl}}} {val}")
    return "\n".join(lines) + "\n"
