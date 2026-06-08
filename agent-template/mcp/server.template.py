"""Backward-compatible MCP server entry point.

New projects should prefer one of:

- ``mcp/adapters/codex/server.py`` for Codex registration.
- ``mcp/adapters/general/server.py`` for a regular MCP client.

Both adapters load the shared registry and shared tool implementations.
"""

from __future__ import annotations

from pathlib import Path
import sys

MCP_DIR = Path(__file__).resolve().parent
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))

from shared.server_factory import create_server  # noqa: E402


mcp = create_server(mode="general")


if __name__ == "__main__":
    mcp.run()
