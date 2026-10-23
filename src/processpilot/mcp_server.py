"""Opt-in Model Context Protocol server for compatible desktop/coding agents.

Install with: pip install -e '.[mcp]'
Run with: python -m processpilot.mcp_server
Transport: stdio (keep stdout clean; MCP frames travel on stdout).
"""
from __future__ import annotations

from .config import Settings
from .engine import classify
from .store import Store

MAX_TICKET_CHARS = 8000


def _validated_text(text: str) -> str:
    value = text.strip()
    if len(value) < 5:
        raise ValueError("Текст обращения должен содержать не менее 5 символов")
    if len(value) > MAX_TICKET_CHARS:
        raise ValueError(f"Текст обращения не должен превышать {MAX_TICKET_CHARS} символов")
    return value


def create_mcp_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install the MCP extra first: pip install -e '.[mcp]'") from exc

    mcp = FastMCP("AI Process Pilot")
    store = Store(Settings.from_env().db_path)
    store.init()

    @mcp.tool()
    def preview_ticket(text: str) -> dict:
        """Classify an incoming request WITHOUT saving it to the database."""
        return classify(_validated_text(text)).to_dict()

    @mcp.tool()
    def get_work_queue(limit: int = 20) -> list[dict]:
        """Read existing tickets (max 100), without exposing raw phone/email values."""
        return store.list(max(1, min(limit, 100)))

    @mcp.tool()
    def get_process_metrics() -> dict:
        """Read workflow metrics and assumptions, without changing data."""
        return store.stats()

    return mcp


def main() -> None:
    create_mcp_server().run(transport="stdio")


if __name__ == "__main__":
    main()
