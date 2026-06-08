"""Default orchestrator mapping.

This mapping passes the previous agent output forward as the next step's
``task_input``. Replace or extend it when a step needs a stricter handoff.
"""

from __future__ import annotations

from typing import Any


JsonObject = dict[str, Any]


def map_input(
    previous_agent_output: JsonObject,
    next_step: JsonObject,
    workflow_state: JsonObject,
) -> JsonObject:
    """Build task_input for the next normal step."""

    return {
        "source": "previous_step_output",
        "next_step_id": next_step["id"],
        "previous_agent_output": previous_agent_output,
        "available_prior_outputs": list(workflow_state.get("outputs", {}).keys()),
    }
