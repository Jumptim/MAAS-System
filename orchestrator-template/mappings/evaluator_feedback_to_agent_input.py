"""Map evaluator feedback into the selected retry agent input."""

from __future__ import annotations

from typing import Any


JsonObject = dict[str, Any]


def map_input(
    previous_agent_output: JsonObject,
    next_step: JsonObject,
    workflow_state: JsonObject,
) -> JsonObject:
    """Build retry task_input from evaluator feedback."""

    evaluator_result = previous_agent_output.get("result", {})
    target_step_id = evaluator_result.get("target_step_id") or next_step["id"]

    return {
        "source": "evaluator_feedback",
        "next_step_id": next_step["id"],
        "target_step_id": target_step_id,
        "revision_feedback": evaluator_result.get("feedback", ""),
        "evaluator_output": previous_agent_output,
        "prior_outputs": workflow_state.get("outputs", {}),
    }
