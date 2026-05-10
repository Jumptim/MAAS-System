"""Template runtime for one MAAS agent.

The runtime belongs to the agent. It wraps raw LLM result JSON into the common
agent output contract, validates it, and optionally asks the LLM to repair only
format/schema errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

try:
    from .validate_output import (
        load_json_file,
        parse_json_text,
        validate_agent_output,
        validate_result,
    )
except ImportError:  # pragma: no cover - allows running this file directly
    from validate_output import (  # type: ignore
        load_json_file,
        parse_json_text,
        validate_agent_output,
        validate_result,
    )


JsonObject = dict[str, Any]
LlmCallable = Callable[[str], str]


@dataclass(frozen=True)
class AgentRuntimeConfig:
    agent_id: str
    parent_workflow_step_id: str
    agent_type: str
    agent_output_schema_path: Path
    result_schema_path: Path
    repair_prompt_path: Path
    max_repair_attempts: int = 2
    invalid_decision: str = "iterate"


class AgentRuntime:
    """Deterministic contract gate around one agent's LLM call."""

    def __init__(self, config: AgentRuntimeConfig) -> None:
        self.config = config
        self.agent_output_schema = load_json_file(config.agent_output_schema_path)
        self.result_schema = load_json_file(config.result_schema_path)
        self.repair_prompt_template = config.repair_prompt_path.read_text(encoding="utf-8")

    def run(self, llm: LlmCallable, prompt: str) -> JsonObject:
        """Run the LLM, repair schema errors if needed, and return agent_output."""

        try:
            raw_text = llm(prompt)
        except Exception as exc:  # pragma: no cover - runtime integration specific
            return self._failed_output([f"LLM call failed: {exc}"])

        raw_attempt = raw_text
        last_errors: list[str] = []

        for attempt_index in range(self.config.max_repair_attempts + 1):
            result, errors = self._parse_and_validate_result(raw_attempt)
            if result is not None and not errors:
                status = "valid" if attempt_index == 0 else "repaired"
                return self._valid_output(result=result, status=status)

            last_errors = errors

            if attempt_index >= self.config.max_repair_attempts:
                break

            repair_prompt = self._build_repair_prompt(raw_attempt, errors)
            try:
                raw_attempt = llm(repair_prompt)
            except Exception as exc:  # pragma: no cover - runtime integration specific
                return self._failed_output([f"LLM repair call failed: {exc}"])

        return self._invalid_output(last_errors)

    def _parse_and_validate_result(self, raw_text: str) -> tuple[JsonObject | None, list[str]]:
        result, parse_errors = parse_json_text(raw_text)
        if parse_errors:
            return None, parse_errors

        assert result is not None
        schema_errors = validate_result(result, self.result_schema)

        if self.config.agent_type == "evaluator":
            decision = result.get("decision")
            if decision not in {"continue", "iterate", "fail"}:
                schema_errors.append(
                    "decision: evaluator result must include one of "
                    "'continue', 'iterate', or 'fail'."
                )
            target_step_id = result.get("target_step_id")
            if decision == "iterate" and not (
                isinstance(target_step_id, str) and target_step_id.strip()
            ):
                schema_errors.append(
                    "target_step_id: evaluator result must include a non-empty "
                    "target_step_id when decision is 'iterate'."
                )
            feedback = result.get("feedback")
            if not isinstance(feedback, str):
                schema_errors.append("feedback: evaluator result must include a string feedback field.")

        return result, schema_errors

    def _valid_output(self, result: JsonObject, status: str) -> JsonObject:
        if self.config.agent_type == "evaluator":
            decision = result["decision"]
            decision_source = "evaluator_judgement"
            target_step_id = result.get("target_step_id")
        else:
            decision = "continue"
            decision_source = "runtime_contract_gate"
            target_step_id = None

        output = self._wrap_output(
            status=status,
            decision=decision,
            decision_source=decision_source,
            target_step_id=target_step_id,
            result=result,
            warnings=[],
            errors=[],
        )
        wrapper_errors = validate_agent_output(output, self.agent_output_schema)
        if wrapper_errors:
            return self._failed_output(wrapper_errors)
        return output

    def _invalid_output(self, errors: list[str]) -> JsonObject:
        output = self._wrap_output(
            status="invalid",
            decision=self.config.invalid_decision,
            decision_source="runtime_contract_gate",
            target_step_id=None,
            result={},
            warnings=[],
            errors=errors,
        )
        wrapper_errors = validate_agent_output(output, self.agent_output_schema)
        if wrapper_errors:
            return self._failed_output(wrapper_errors + errors)
        return output

    def _failed_output(self, errors: list[str]) -> JsonObject:
        return self._wrap_output(
            status="failed",
            decision="fail",
            decision_source="runtime_contract_gate",
            target_step_id=None,
            result={},
            warnings=[],
            errors=errors,
        )

    def _wrap_output(
        self,
        status: str,
        decision: str,
        decision_source: str,
        target_step_id: str | None,
        result: JsonObject,
        warnings: list[str],
        errors: list[str],
    ) -> JsonObject:
        return {
            "agent_id": self.config.agent_id,
            "parent_workflow_step_id": self.config.parent_workflow_step_id,
            "agent_type": self.config.agent_type,
            "status": status,
            "decision": decision,
            "decision_source": decision_source,
            "target_step_id": target_step_id,
            "result": result,
            "warnings": warnings,
            "errors": errors,
            "memory_refs": [],
            "log_refs": [],
        }

    def _build_repair_prompt(self, previous_output: str, errors: list[str]) -> str:
        rendered_errors = "\n".join(f"- {error}" for error in errors)
        return self.repair_prompt_template.format(
            previous_output=previous_output,
            validation_errors=rendered_errors,
        )
