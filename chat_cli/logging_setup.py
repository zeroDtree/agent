"""Reduce noisy library logs during interactive CLI use."""

from __future__ import annotations

import logging


def quiet_http_client_loggers() -> None:
    """Silence chatty HTTP/MCP INFO lines on the console (sessions, protocol version, etc.)."""
    for name in (
        "httpx",
        "httpcore",
        "urllib3",
        "openai",
        "mcp",
        "mcp.client",
        "mcp.client.streamable_http",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)
