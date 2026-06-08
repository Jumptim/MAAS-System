# Codex MCP Adapter

Use `server.py` as the Codex-facing MCP server entry point.

This template intentionally avoids writing to any global Codex configuration.
When installing a concrete agent, copy or render `mcp.config.yaml` with absolute
paths and register it in the Codex environment you use.

The adapter does not implement tools directly. It loads:

```text
../../shared/tool_registry.yaml
../../shared/tools/
../../shared/schemas/
```
