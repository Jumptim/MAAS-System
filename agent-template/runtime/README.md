# Agent Runtime Template

This runtime is the agent's output contract gate. It is not the orchestrator and
does not judge task quality.

## Responsibilities

- Receive raw LLM result text.
- Parse the text as a JSON object.
- Validate the parsed object against `schemas/result.schema.json`.
- Wrap the result in the common `schemas/agent_output.schema.json` envelope.
- Validate the final envelope.
- Use `prompts/output_repair_prompt.md` for temporary repair attempts.

## Decision Ownership

Normal agents do not make workflow quality decisions. For normal agents, the
runtime sets:

```json
{
  "decision": "continue",
  "decision_source": "runtime_contract_gate"
}
```

when the result contract is valid or repaired.

Evaluator agents still use the same template. Their LLM output is a result
object whose task-specific schema should include `decision`, `target_step_id`,
and `feedback`. The runtime extracts the decision and target step, validates the
minimal evaluator semantics, and sets:

```json
{
  "decision_source": "evaluator_judgement"
}
```

When an evaluator returns `decision: iterate`, `target_step_id` must be a
non-empty string. The orchestrator, not the evaluator runtime, checks whether
that target step is allowed by the workflow.

## Repair Scope

Repair prompts are temporary. They must not be written back to the base agent
prompt, agent config, or long-term memory. Store repair attempts in logs only.

Runtime repair is different from workflow iteration:

- Runtime repair fixes JSON/schema contract errors inside one agent call.
- Workflow iteration is a new orchestrator step caused by a routed decision.
