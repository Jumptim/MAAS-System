# MAAS System

This repository is the workspace for a multi-agent system.

At the moment, it contains one reusable agent template and one orchestrator template. The agent template defines the structure for a single agent, while the orchestrator template defines how multiple agent steps connect, exchange outputs, and run inside a larger workflow.

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
  orchestrator-template/
    README.md
    main.py
    workflow.yaml
    mappings/
    schemas/
    logs/
```

## Current Layer

`agent-template/` is the blueprint for one agent. Copy it when creating a new agent, then customize:

- `agent.yaml` for role, task boundary, allowed skills, tools, resources, memory, and logging
- `skills/` for reusable capability manifests
- `mcp/` for MCP server and tool templates
- `rag/` for local knowledge resources
- `schemas/` for input, output, memory, log, RAG, skill, and MCP contracts

## Orchestrator Layer

`orchestrator-template/` is the blueprint for the workflow driver. Use it to define:

- `main.py` as the orchestrator entry point
- `workflow.yaml` for workflow steps, allowed decisions, and iteration limits
- `mappings/` for deterministic agent-output to agent-input conversion code
- `schemas/workflow.schema.json` for validating the workflow configuration
- `schemas/orchestrator_log_event.schema.json` for validating workflow-level log events
- `logs/` for route-level workflow logs

This keeps the reusable single-agent template separate from the top-level multi-agent orchestration.

## Runtime Connection

The intended runtime connection is:

```text
orchestrator-template/main.py
  -> reads orchestrator-template/workflow.yaml
  -> uses each step's agent.path and agent.config to find agent.yaml
  -> calls agent-template/runtime/prompt_builder.py
  -> prompt_builder.py reads agent.yaml, prompts, skills, MCP, RAG, and memory config
  -> agent-template/runtime/agent_runtime.py validates and wraps the LLM result
  -> main.py routes the final agent output through workflow.yaml decisions
  -> orchestrator-template/mappings/*.py builds the next agent input
```

`workflow.yaml` tells the orchestrator where each agent lives. `agent.yaml`
tells the agent-side builder where that agent's own prompt, schema, skill,
tool, resource, memory, and logging files live.
