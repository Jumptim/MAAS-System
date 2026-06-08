"""Backward-compatible wrapper for the shared template MCP tool."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

MCP_DIR = Path(__file__).resolve().parents[1]
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))

from shared.tools.tool_template import TOOL_ID, run  # noqa: E402,F401


def run_legacy(arguments: dict[str, Any]) -> dict[str, Any]:
    """Call the shared implementation from the old template path."""

    return run(arguments)
