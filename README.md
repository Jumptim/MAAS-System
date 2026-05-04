# MAAS System

This repository is the workspace for a multi-agent system.

At the moment, it contains one reusable agent template. The template defines the structure for a single agent, while future system-level folders can define how multiple agents connect, exchange outputs, and run inside a larger workflow.

## Structure

```text
MAAS System/
  README.md
  agent-template/
    README.md
    agent.yaml
    skills/
    mcp/
    rag/
    memory/
    logs/
    prompts/
    schemas/
```

## Current Layer

`agent-template/` is the blueprint for one agent. Copy it when creating a new agent, then customize:

- `agent.yaml` for role, task boundary, allowed skills, tools, resources, memory, and logging
- `skills/` for reusable capability manifests
- `mcp/` for MCP server and tool templates
- `rag/` for local knowledge resources
- `schemas/` for input, output, memory, log, RAG, skill, and MCP contracts

## Future Connection Layer

When the project grows beyond one template, keep cross-agent logic outside `agent-template/`. Good candidates are:

- `workflows/` for parent workflow definitions
- `connections/` for agent-to-agent contracts and handoff schemas
- `agents/` for concrete agent instances copied from the template

This keeps the reusable single-agent template separate from the top-level multi-agent orchestration.
