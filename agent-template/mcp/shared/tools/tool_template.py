"""Template MCP tool implementation shared by every adapter."""

from __future__ import annotations

from typing import Any


TOOL_ID = "tool.template"


def run(arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute the template tool.

    Replace this implementation with one narrow capability. Keep validation and
    permission checks close to the action so every adapter gets the same safety
    behavior.
    """

    input_text = arguments.get("input_text", "")
    return {
        "tool_id": TOOL_ID,
        "status": "success",
        "result": {
            "echo": input_text,
        },
        "errors": [],
    }
