"""
Template MCP server for one agent template.

Fill in the TODO sections with real tools. Keep orchestration decisions out of
this file. The parent workflow, agent.yaml, and skill manifests decide what is
allowed to run.
"""

from __future__ import annotations

from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise SystemExit("Install MCP with: python -m pip install mcp") from exc


mcp = FastMCP("TODO_AGENT_MCP_SERVER_NAME")


@mcp.tool(name="tool.template")
def tool_template(input_text: str) -> dict[str, Any]:
    """
    Example MCP tool.

    TODO:
    - replace this with a real tool
    - validate input
    - enforce permissions
    - return schema-compatible output
    """
    return {
        "status": "success",
        "result": {
            "echo": input_text
        },
        "errors": []
    }


if __name__ == "__main__":
    mcp.run()

