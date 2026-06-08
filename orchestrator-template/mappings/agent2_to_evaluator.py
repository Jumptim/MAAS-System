"""Map agent_2 output into evaluator input."""

from __future__ import annotations

from typing import Any


JsonObject = dict[str, Any]


def map_input(
    previous_agent_output: JsonObject,
    next_step: JsonObject,
    workflow_state: JsonObject,
) -> JsonObject:
    """Build evaluator task_input from the output that should be evaluated."""

    return {
        "source": "agent_output_for_evaluation",
        "next_step_id": next_step["id"],
        "output_to_evaluate": previous_agent_output,
        "prior_outputs": workflow_state.get("outputs", {}),
        "evaluation_instruction": (
            "Evaluate whether the previous output is acceptable. Return a "
            "decision, target_step_id, and feedback according to the evaluator "
            "result schema."
        ),
    }
