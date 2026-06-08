"""Create MCP servers from the shared tool registry."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependency guard for template use
    raise RuntimeError("Install PyYAML with: pip install pyyaml") from exc

JsonObject = dict[str, Any]


def load_yaml_file(path: str | Path) -> JsonObject:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected YAML object in file: {path}")
    return value


def default_registry_path() -> Path:
    return Path(__file__).resolve().parent / "tool_registry.yaml"


def load_callable(module_name: str, function_name: str) -> Callable[[JsonObject], JsonObject]:
    module = importlib.import_module(module_name)
    tool_callable = getattr(module, function_name)
    if not callable(tool_callable):
        raise TypeError(f"{module_name}.{function_name} is not callable")
    return tool_callable


def create_tool_wrapper(tool_id: str, tool_callable: Callable[[JsonObject], JsonObject]):
    def wrapper(arguments: JsonObject | None = None) -> JsonObject:
        return tool_callable(arguments or {})

    wrapper.__name__ = tool_id.replace(".", "_").replace("-", "_")
    wrapper.__doc__ = f"Run MCP tool {tool_id}."
    return wrapper


def create_server(
    mode: str = "general",
    registry_path: str | Path | None = None,
):
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - dependency guard for template use
        raise RuntimeError("Install MCP with: python -m pip install mcp") from exc

    registry = load_yaml_file(registry_path or default_registry_path())
    server_config = registry.get("server", {})
    server_name = f"{server_config.get('name', 'agent-mcp-server')}:{mode}"
    mcp = FastMCP(server_name)

    for tool in registry.get("tools", []):
        tool_id = tool["id"]
        tool_callable = load_callable(tool["module"], tool.get("function", "run"))
        wrapper = create_tool_wrapper(tool_id, tool_callable)
        mcp.tool(name=tool_id)(wrapper)

    return mcp
