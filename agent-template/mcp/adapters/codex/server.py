"""Codex-facing MCP server entry point."""

from __future__ import annotations

from pathlib import Path
import sys

MCP_DIR = Path(__file__).resolve().parents[2]
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))

from shared.server_factory import create_server  # noqa: E402


mcp = create_server(mode="codex")


if __name__ == "__main__":
    mcp.run()
