from __future__ import annotations

import os

_cached: dict[str, str] | None = None


def cors_headers() -> dict[str, str]:
    global _cached
    if _cached is None:
        origin = os.environ.get("CORS_ORIGIN", "*")
        _cached = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, x-functions-key",
            "Access-Control-Expose-Headers": "Cache-Control",
        }
    return _cached
