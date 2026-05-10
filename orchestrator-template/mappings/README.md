# Workflow Mappings

This folder is reserved for mapping code.

A mapping converts one or more previous agent outputs into the next agent input
format. It should be deterministic orchestrator-side logic, not free-form agent
reasoning.

Examples of mapping responsibilities:

- selecting fields from a previous agent output
- renaming fields for the next agent input
- merging outputs from multiple previous steps
- adding evaluator feedback to a retry input
- adding workflow-level constraints
- normalizing or cleaning structured values

`workflow.yaml` can reference mapping implementations by `mapping_id`.

Example:

```yaml
input:
  source: previous_step_output
  mapping:
    mode: custom
    mapping_id: agent2_to_evaluator
```

If a step uses `mode: orchestrator_default`, the orchestrator applies the default
handoff rule defined by your system.

## Evaluator Feedback Handoff

Evaluator agents should not construct the next agent's full input. They should
return a minimal result containing:

```json
{
  "decision": "iterate",
  "target_step_id": "agent_1",
  "feedback": "What should be revised and why."
}
```

When an evaluator chooses a dynamic retry target, the orchestrator validates
`target_step_id` against the current transition's `allowed_next_steps`. A custom
mapping then builds the target agent input from:

- the original workflow input, when needed
- the output being evaluated
- the evaluator feedback
- the chosen `target_step_id`

Example transition-level mapping:

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
