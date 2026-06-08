# MCP Template

This folder separates MCP capability code from client-specific registration.

```text
mcp/
  shared/
    tool_registry.yaml
    server_factory.py
    tools/
    schemas/
  adapters/
    codex/
      server.py
      mcp.config.yaml
    general/
      server.py
      config.example.yaml
```

## Design Rule

Put reusable MCP tool logic in `shared/`. Put only startup and client
registration details in `adapters/`.

- `shared/tools/`: real tool implementations
- `shared/schemas/`: tool input and output contracts
- `shared/tool_registry.yaml`: one registry used by both adapters
- `shared/server_factory.py`: builds a FastMCP server from the registry
- `adapters/codex/`: Codex-oriented server entry point and config template
- `adapters/general/`: regular MCP client entry point and config example

The compatibility files `server.template.py` and `tools/tool.template.py`
delegate to `shared/` so older paths still work while new code avoids duplicate
tool implementations.

## Codex Adapter

Use `adapters/codex/server.py` as the server command target when registering
this MCP server with Codex. Keep machine-specific absolute paths out of this
template; copy or render `adapters/codex/mcp.config.yaml` during installation.

## General Adapter

Use `adapters/general/server.py` for a normal MCP client or local development.
The general adapter reads the same shared registry and tool implementations as
the Codex adapter.
