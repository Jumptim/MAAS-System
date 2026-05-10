# Orchestrator Template

This folder defines the orchestrator layer for a MAAS system.

The orchestrator layer does not define the internal structure of an agent. The
agent structure stays in `agent-template/`. This layer defines how fixed agents
are connected, which decisions are allowed, and how `main.py` drives the
workflow.

## Responsibility

Use this folder to define:

- workflow steps and their order
- concrete agent identities used by each step
- allowed `continue`, `iterate`, and `fail` transitions
- maximum iteration limits
- workflow-level policy for invalid output, failed output, mapping failure,
  invalid decisions, disallowed transitions, and iteration limits
- input handoff policy between steps
- orchestrator-level logs for workflow routing events

Do not use this folder to define:

- agent prompts
- agent skills
- MCP tools
- RAG resources
- agent memory
- agent internal logs

Those belong in `agent-template/`.

## Structure

```text
orchestrator-template/
  README.md
  main.py
  workflow.yaml
  mappings/
    README.md
  schemas/
    workflow.schema.json
    orchestrator_log_event.schema.json
  logs/
    README.md
    .gitkeep
```

## What Schemas Mean Here

Schemas are formal contracts. They describe what shape a file or runtime record
must have.

In this orchestrator layer, schemas do not execute the workflow and do not
transform agent outputs into agent inputs. The `main.py` orchestrator can use
them to
validate:

- whether `workflow.yaml` is structurally valid
- whether orchestrator log events have the expected shape

The actual mapping logic should be implemented by orchestrator code or custom
mapping code referenced by the workflow.

Agent-level logs stay inside `agent-template/logs/`. Orchestrator logs should
only record routing-level events such as workflow start, step start, mapping
selection, agent decision, policy application, accepted transition, iteration
count, and workflow finish. They should reference agent outputs or agent logs
instead of copying full agent outputs.

## Decision Meaning

All final agent outputs expose the same workflow decision actions:

- `continue`: the current step is complete and may move to an allowed next step
- `iterate`: the workflow should run an allowed retry or revision step
- `fail`: the workflow cannot reliably continue from this step

Normal agents do not judge task quality. Their agent runtime sets the decision
from the output contract gate:

```text
valid/repaired -> continue
invalid -> iterate or fail, according to agent configuration and workflow policy
failed -> fail
```

Evaluator agents use the same agent template, but their task-specific result
contains the quality judgement. The evaluator runtime validates that judgement
and promotes it to the final agent output as:

```text
decision_source = evaluator_judgement
```

## Orchestrator Policy

The orchestrator policy is a governance layer, not a content evaluator. It
should only handle deterministic workflow safety rules:

- `on_agent_output_invalid`: what to do when an agent returns `status: invalid`
- `on_agent_output_failed`: what to do when an agent returns `status: failed`
- `on_invalid_decision`: what to do when a decision is missing or not one of
  `continue`, `iterate`, or `fail`
- `on_disallowed_transition`: what to do when a valid decision is not allowed by
  the current step
- `on_mapping_failed`: what to do when an agent output cannot be mapped into
  the next agent input
- `on_iteration_limit_reached`: what to do when step-level or workflow-level
  iteration limits are reached
- `max_total_iterations`: maximum total workflow iterations

Content quality rules belong in evaluator agents, not in the orchestrator
policy. This keeps the system rule-governed without turning the orchestrator
into a central intelligence.

## Agent Connection

The orchestrator consumes only the final agent output contract:

```text
agent_output.status
agent_output.decision
agent_output.decision_source
agent_output.target_step_id
agent_output.result
```

It validates the envelope, applies `orchestrator_policy`, checks the current
step's `allowed_decisions`, enforces iteration limits, and routes to the next
step. The orchestrator should not inspect or repair an agent's internal prompt,
skills, memory, or runtime repair attempts.

## Dynamic Iterate Targets

Evaluator agents may choose which allowed step should receive a revision by
returning `target_step_id` with `decision: iterate`. The workflow must explicitly
allow those targets:

```yaml
allowed_decisions:
  iterate:
    allowed_next_steps:
      - agent_1
      - agent_2
    max_iterations: 3
    mapping:
      mode: custom
      mapping_id: evaluator_feedback_to_agent_input
```

The orchestrator accepts the evaluator's target only when it appears in
`allowed_next_steps`. If the target is missing or not allowed, the orchestrator
applies `on_disallowed_transition`.

The transition mapping is responsible for turning evaluator feedback and prior
outputs into the next target agent's input. Evaluator agents provide feedback;
they do not build another agent's full prompt or runtime input directly.
