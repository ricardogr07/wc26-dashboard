from __future__ import annotations

import os


def cors_headers() -> dict[str, str]:
    origin = os.environ.get("CORS_ORIGIN", "*")
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-functions-key",
    }
