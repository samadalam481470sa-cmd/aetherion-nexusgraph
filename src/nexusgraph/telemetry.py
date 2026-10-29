"""Small ASGI-level request metrics, deliberately excluding sensitive identifiers."""
from __future__ import annotations

import hmac
import os
from collections import Counter
from threading import Lock

from fastapi import HTTPException, Request
from fastapi.responses import PlainTextResponse

_counts: Counter[tuple[str, str]] = Counter()
_lock = Lock()


async def record_http(request: Request, call_next):
    response = await call_next(request)
    # Only aggregate by HTTP method/status: avoid paths containing tenant/customer identifiers.
    with _lock:
        _counts[(request.method, str(response.status_code))] += 1
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


async def metrics(request: Request):
    expected = os.getenv("NEXUSGRAPH_METRICS_TOKEN")
    if not expected:
        raise HTTPException(status_code=404, detail="Metrics disabled")

    supplied = request.headers.get("X-Metrics-Token", "")
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=401, detail="Unauthorized")
    with _lock:
        snapshot = list(_counts.items())
    lines = [
        "# HELP nexusgraph_http_requests_total HTTP requests by method and status",
        "# TYPE nexusgraph_http_requests_total counter",
    ]
    for (method, status), count in snapshot:
        lines.append(
            f'nexusgraph_http_requests_total{{method="{method}",status="{status}"}} {count}'
        )
    return PlainTextResponse("\n".join(lines) + "\n")
