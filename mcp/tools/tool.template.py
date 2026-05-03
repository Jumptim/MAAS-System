"""
Template for one MCP tool implementation.

Keep each tool narrow. A tool should expose one controlled capability, not run
the agent workflow.
"""

from __future__ import annotations

from typing import Any


TOOL_ID = "tool.template"


def run(arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Execute the tool.

    TODO:
    - define required arguments
    - validate permissions
    - perform the tool action
    - return structured output
    """
    return {
        "tool_id": TOOL_ID,
        "status": "success",
        "result": {},
        "errors": []
    }

