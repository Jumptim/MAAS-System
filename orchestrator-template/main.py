"""Template entry point for the MAAS workflow orchestrator.

The orchestrator owns workflow routing. It reads ``workflow.yaml``, finds the
agent folder for each step, asks the agent-side prompt builder to prepare the
prompt/runtime config, then routes according to the final agent output.

This template does not include a real LLM client. Pass one to ``run_workflow``
from your application code, or use ``--dry-run`` to verify configuration and
show the first prepared prompt.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependency guard for template use
    raise RuntimeError("Install PyYAML with: pip install pyyaml") from exc

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover - dependency guard for template use
    raise RuntimeError("Install jsonschema with: pip install jsonschema") from exc


JsonObject = dict[str, Any]
LlmCallable = Callable[[str], str]


def load_yaml_file(path: str | Path) -> JsonObject:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected YAML object in file: {path}")
    return value


def load_json_file(path: str | Path) -> JsonObject:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object in file: {path}")
    return value


def validate_against_schema(instance: JsonObject, schema_path: str | Path) -> None:
    schema = load_json_file(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
    if errors:
        rendered = []
        for error in errors:
            path = ".".join(str(part) for part in error.absolute_path) or "$"
            rendered.append(f"{path}: {error.message}")
        raise ValueError("Schema validation failed:\n" + "\n".join(rendered))


def load_module(module_path: Path, module_name: str):
    runtime_dir = str(module_path.parent)
    if runtime_dir not in sys.path:
        sys.path.insert(0, runtime_dir)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def load_workflow(workflow_path: str | Path) -> JsonObject:
    workflow_path = Path(workflow_path).resolve()
    workflow = load_yaml_file(workflow_path)
    validate_against_schema(
        workflow,
        workflow_path.parent / "schemas" / "workflow.schema.json",
    )
    return workflow


def load_initial_input(workflow_dir: Path, workflow: JsonObject, input_override: str | None) -> JsonObject:
    input_path_value = input_override or workflow.get("workflow_input", {}).get("path")
    if not input_path_value:
        raise ValueError("Provide --input or define workflow_input.path in workflow.yaml")

    input_path = Path(input_path_value)
    if not input_path.is_absolute():
        input_path = workflow_dir / input_path

    if input_path.suffix.lower() == ".json":
        content: Any = load_json_file(input_path)
    else:
        content = {
            "text": input_path.read_text(encoding="utf-8"),
        }

    return {
        "source_path": str(input_path.resolve()),
        "content": content,
    }


def normalize_agent_type(workflow_role: str) -> str:
    if workflow_role == "evaluator_agent":
        return "evaluator"
    return "normal"


def build_agent_input(step: JsonObject, task_input: JsonObject) -> JsonObject:
    execution = step.get("execution", {})
    return {
        "task_input": task_input,
        "parent_workflow_step_id": step["id"],
        "constraints": execution.get("constraints", []),
    }


def prepare_agent_invocation(workflow_dir: Path, step: JsonObject, task_input: JsonObject) -> JsonObject:
    agent_spec = step["agent"]
    agent_dir = Path(agent_spec["path"])
    if not agent_dir.is_absolute():
        agent_dir = (workflow_dir / agent_dir).resolve()

    builder_path = agent_dir / "runtime" / "prompt_builder.py"
    prompt_builder = load_module(builder_path, f"{step['id']}_prompt_builder")
    agent_config = prompt_builder.load_agent_config(agent_dir, agent_spec["config"])

    agent_input = build_agent_input(step, task_input)
    input_schema_path = agent_dir / agent_config["input"]["schema"]
    validate_against_schema(agent_input, input_schema_path)

    agent_type = normalize_agent_type(agent_spec["role"])
    runtime_config = prompt_builder.build_runtime_config(
        agent_dir=agent_dir,
        parent_workflow_step_id=step["id"],
        agent_config=agent_config,
        agent_type_override=agent_type,
    )
    prompt = prompt_builder.build_prompt(
        agent_dir,
        agent_input,
        agent_config,
        result_schema_path=runtime_config.result_schema_path,
    )

    return {
        "step_id": step["id"],
        "agent_dir": agent_dir,
        "agent_input": agent_input,
        "prompt": prompt,
        "runtime_config": runtime_config,
    }


def run_agent(prepared: JsonObject, llm: LlmCallable) -> JsonObject:
    runtime_path = prepared["agent_dir"] / "runtime" / "agent_runtime.py"
    runtime_module = load_module(runtime_path, f"{prepared['step_id']}_agent_runtime")
    runtime = runtime_module.AgentRuntime(prepared["runtime_config"])
    return runtime.run(llm, prepared["prompt"])


def find_step(workflow: JsonObject, step_id: str) -> JsonObject:
    for step in workflow["steps"]:
        if step["id"] == step_id:
            return step
    raise KeyError(f"Unknown workflow step: {step_id}")


def policy_terminal_result(
    terminal_step: str,
    status: str,
    agent_output: JsonObject,
    workflow_state: JsonObject,
    reason: str,
) -> JsonObject:
    return {
        "terminal_step": terminal_step,
        "status": status,
        "last_agent_output": agent_output,
        "workflow_state": workflow_state,
        "reason": reason,
    }


def output_with_policy_decision(agent_output: JsonObject, decision: str, reason: str) -> JsonObject:
    updated = dict(agent_output)
    updated["decision"] = decision
    updated["decision_source"] = "orchestrator_policy"
    updated["target_step_id"] = None
    updated["warnings"] = list(updated.get("warnings", [])) + [reason]
    return updated


def apply_terminal_policy(
    workflow: JsonObject,
    policy_key: str,
    default_action: str,
    reason: str,
    agent_output: JsonObject,
    workflow_state: JsonObject,
) -> JsonObject:
    action = workflow.get("orchestrator_policy", {}).get(policy_key, default_action)
    if action == "stop_for_human_review":
        reviewed_output = output_with_policy_decision(agent_output, "fail", reason)
        return policy_terminal_result(
            terminal_step="human_review_required",
            status="human_review_required",
            agent_output=reviewed_output,
            workflow_state=workflow_state,
            reason=reason,
        )

    failed_output = output_with_policy_decision(agent_output, "fail", reason)
    return policy_terminal_result(
        terminal_step="workflow_failed",
        status="failed",
        agent_output=failed_output,
        workflow_state=workflow_state,
        reason=reason,
    )


def apply_orchestrator_policy(
    workflow: JsonObject,
    current_step: JsonObject,
    agent_output: JsonObject,
    workflow_state: JsonObject,
) -> tuple[JsonObject, JsonObject | None]:
    policy = workflow.get("orchestrator_policy", {})
    status = agent_output.get("status")
    decision = agent_output.get("decision")

    if status == "failed":
        terminal = apply_terminal_policy(
            workflow=workflow,
            policy_key="on_agent_output_failed",
            default_action="fail_workflow",
            reason=f"Agent output failed at step {current_step['id']}.",
            agent_output=agent_output,
            workflow_state=workflow_state,
        )
        return terminal["last_agent_output"], terminal

    if status == "invalid":
        action = policy.get("on_agent_output_invalid", "fail_workflow")
        reason = f"Agent output was invalid at step {current_step['id']}."
        if action == "allow_step_iteration":
            return output_with_policy_decision(agent_output, "iterate", reason), None
        terminal = apply_terminal_policy(
            workflow=workflow,
            policy_key="on_agent_output_invalid",
            default_action="fail_workflow",
            reason=reason,
            agent_output=agent_output,
            workflow_state=workflow_state,
        )
        return terminal["last_agent_output"], terminal

    if decision not in {"continue", "iterate", "fail"}:
        terminal = apply_terminal_policy(
            workflow=workflow,
            policy_key="on_invalid_decision",
            default_action="fail_workflow",
            reason=f"Invalid decision {decision!r} at step {current_step['id']}.",
            agent_output=agent_output,
            workflow_state=workflow_state,
        )
        return terminal["last_agent_output"], terminal

    return agent_output, None


def enforce_iteration_limits(
    workflow: JsonObject,
    current_step: JsonObject,
    agent_output: JsonObject,
    workflow_state: JsonObject,
) -> JsonObject | None:
    if agent_output.get("decision") != "iterate":
        return None

    workflow_state["total_iterations"] = workflow_state.get("total_iterations", 0) + 1
    max_total = workflow.get("orchestrator_policy", {}).get("max_total_iterations")
    if max_total is not None and workflow_state["total_iterations"] > max_total:
        return apply_terminal_policy(
            workflow=workflow,
            policy_key="on_iteration_limit_reached",
            default_action="fail_workflow",
            reason="Workflow total iteration limit reached.",
            agent_output=agent_output,
            workflow_state=workflow_state,
        )

    step_id = current_step["id"]
    workflow_state["iterations"][step_id] = workflow_state["iterations"].get(step_id, 0) + 1
    transition = current_step["allowed_decisions"]["iterate"]
    max_step_iterations = transition.get("max_iterations")
    if max_step_iterations is not None and workflow_state["iterations"][step_id] > max_step_iterations:
        return apply_terminal_policy(
            workflow=workflow,
            policy_key="on_iteration_limit_reached",
            default_action="fail_workflow",
            reason=f"Step iteration limit reached for {step_id}.",
            agent_output=agent_output,
            workflow_state=workflow_state,
        )

    return None


def choose_next_step(current_step: JsonObject, agent_output: JsonObject) -> str:
    decision = agent_output.get("decision")
    allowed = current_step["allowed_decisions"].get(decision)
    if allowed is None:
        raise ValueError(f"Decision {decision!r} is not allowed for step {current_step['id']}")

    if decision == "iterate" and "allowed_next_steps" in allowed:
        target = agent_output.get("target_step_id")
        if target not in allowed["allowed_next_steps"]:
            raise ValueError(f"Evaluator target {target!r} is not allowed for step {current_step['id']}")
        return target

    return allowed["next_step"]


def map_task_input(
    workflow_dir: Path,
    mapping_config: JsonObject | None,
    previous_agent_output: JsonObject,
    next_step: JsonObject,
    workflow_state: JsonObject,
) -> JsonObject:
    mapping_config = mapping_config or {"mode": "orchestrator_default", "mapping_id": None}
    mapping_id = mapping_config.get("mapping_id") or "default_mapping"
    mapping_path = workflow_dir / "mappings" / f"{mapping_id}.py"
    mapping_module = load_module(mapping_path, f"mapping_{mapping_id}")
    return mapping_module.map_input(
        previous_agent_output=previous_agent_output,
        next_step=next_step,
        workflow_state=workflow_state,
    )


def get_transition_mapping(current_step: JsonObject, agent_output: JsonObject) -> JsonObject | None:
    decision = agent_output["decision"]
    transition = current_step["allowed_decisions"][decision]
    return transition.get("mapping")


def get_step_input_mapping(next_step: JsonObject) -> JsonObject | None:
    return next_step.get("input", {}).get("mapping")


def run_workflow(workflow_path: str | Path, initial_input: JsonObject, llm: LlmCallable) -> JsonObject:
    workflow_path = Path(workflow_path).resolve()
    workflow_dir = workflow_path.parent
    workflow = load_workflow(workflow_path)
    current_step = workflow["steps"][0]
    task_input = initial_input
    workflow_state: JsonObject = {"outputs": {}, "iterations": {}, "total_iterations": 0}

    while True:
        prepared = prepare_agent_invocation(workflow_dir, current_step, task_input)
        agent_output = run_agent(prepared, llm)
        agent_output, policy_terminal = apply_orchestrator_policy(
            workflow=workflow,
            current_step=current_step,
            agent_output=agent_output,
            workflow_state=workflow_state,
        )
        workflow_state["outputs"][current_step["id"]] = agent_output
        if policy_terminal is not None:
            return policy_terminal

        iteration_terminal = enforce_iteration_limits(
            workflow=workflow,
            current_step=current_step,
            agent_output=agent_output,
            workflow_state=workflow_state,
        )
        if iteration_terminal is not None:
            return iteration_terminal

        try:
            next_step_id = choose_next_step(current_step, agent_output)
        except Exception as exc:
            return apply_terminal_policy(
                workflow=workflow,
                policy_key="on_disallowed_transition",
                default_action="fail_workflow",
                reason=str(exc),
                agent_output=agent_output,
                workflow_state=workflow_state,
            )

        if next_step_id in workflow["terminal_steps"]:
            return {
                "terminal_step": next_step_id,
                "status": workflow["terminal_steps"][next_step_id]["status"],
                "last_agent_output": agent_output,
                "workflow_state": workflow_state,
            }

        try:
            next_step = find_step(workflow, next_step_id)
        except Exception as exc:
            return apply_terminal_policy(
                workflow=workflow,
                policy_key="on_disallowed_transition",
                default_action="fail_workflow",
                reason=str(exc),
                agent_output=agent_output,
                workflow_state=workflow_state,
            )

        mapping_config = get_transition_mapping(current_step, agent_output) or get_step_input_mapping(next_step)
        try:
            task_input = map_task_input(
                workflow_dir=workflow_dir,
                mapping_config=mapping_config,
                previous_agent_output=agent_output,
                next_step=next_step,
                workflow_state=workflow_state,
            )
        except Exception as exc:
            return apply_terminal_policy(
                workflow=workflow,
                policy_key="on_mapping_failed",
                default_action="fail_workflow",
                reason=f"Mapping failed from {current_step['id']} to {next_step_id}: {exc}",
                agent_output=agent_output,
                workflow_state=workflow_state,
            )
        current_step = next_step


def main() -> None:
    parser = argparse.ArgumentParser(description="MAAS orchestrator template")
    parser.add_argument("--workflow", default=None, help="Path to workflow.yaml")
    parser.add_argument("--input", default=None, help="Initial input file path")
    parser.add_argument("--dry-run", action="store_true", help="Prepare the first agent prompt without calling an LLM")
    args = parser.parse_args()

    workflow_path = Path(args.workflow).resolve() if args.workflow else Path(__file__).resolve().parent / "workflow.yaml"
    workflow = load_workflow(workflow_path)
    initial_input = load_initial_input(workflow_path.parent, workflow, args.input)
    first_step = workflow["steps"][0]
    prepared = prepare_agent_invocation(workflow_path.parent, first_step, initial_input)

    if args.dry_run:
        print(prepared["prompt"])
        return

    raise RuntimeError(
        "No LLM callable is configured in this template. "
        "Import run_workflow(...) from application code and pass a real llm(prompt)->str callable, "
        "or run this file with --dry-run."
    )


if __name__ == "__main__":
    main()
