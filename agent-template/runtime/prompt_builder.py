"""Agent-side prompt and runtime configuration builder.

This module is the bridge from ``agent.yaml`` to the agent runtime. The
orchestrator chooses which agent folder to run; this builder loads that
agent's own files and prepares the prompt plus ``AgentRuntimeConfig``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependency guard for template use
    raise RuntimeError(
        "The prompt builder requires the 'PyYAML' package. "
        "Install it with: pip install pyyaml"
    ) from exc

try:
    from .agent_runtime import AgentRuntimeConfig
except ImportError:  # pragma: no cover - allows running this file directly
    from agent_runtime import AgentRuntimeConfig  # type: ignore


JsonObject = dict[str, Any]


def load_yaml_file(path: str | Path) -> JsonObject:
    """Load a YAML file and require it to contain a mapping/object."""

    resolved = Path(path)
    with resolved.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected YAML object in file: {resolved}")
    return value


def read_text_file(path: str | Path) -> str:
    """Read a UTF-8 text file."""

    return Path(path).read_text(encoding="utf-8")


def resolve_agent_file(agent_dir: str | Path, relative_path: str) -> Path:
    """Resolve a path declared inside agent.yaml relative to the agent folder."""

    return (Path(agent_dir) / relative_path).resolve()


def load_agent_config(agent_dir: str | Path, config_name: str = "agent.yaml") -> JsonObject:
    """Load an agent's ``agent.yaml``."""

    return load_yaml_file(Path(agent_dir) / config_name)


def load_skill_manifests(agent_dir: str | Path, agent_config: JsonObject) -> list[JsonObject]:
    """Load skill manifests allowed by the agent config."""

    manifests: list[JsonObject] = []
    for skill_id in agent_config.get("allowed_skills", []):
        manifest_path = Path(agent_dir) / "skills" / f"{skill_id}.yaml"
        if not manifest_path.exists() and skill_id == "skill.template":
            manifest_path = Path(agent_dir) / "skills" / "skill.template.yaml"
        manifests.append(load_yaml_file(manifest_path))
    return manifests


def load_agent_side_configs(agent_dir: str | Path, agent_config: JsonObject) -> JsonObject:
    """Load optional agent-side configuration files referenced by agent.yaml."""

    configs: JsonObject = {}

    memory_config = agent_config.get("memory", {}).get("config")
    if memory_config:
        configs["memory"] = load_yaml_file(resolve_agent_file(agent_dir, memory_config))

    mcp_config_path = Path(agent_dir) / "mcp" / "mcp.config.yaml"
    if mcp_config_path.exists():
        configs["mcp"] = load_yaml_file(mcp_config_path)

    rag_config_path = Path(agent_dir) / "rag" / "resources.yaml"
    if rag_config_path.exists():
        configs["rag"] = load_yaml_file(rag_config_path)

    configs["skills"] = load_skill_manifests(agent_dir, agent_config)
    return configs


def build_prompt(
    agent_dir: str | Path,
    agent_input: JsonObject,
    agent_config: JsonObject | None = None,
    result_schema_path: str | Path | None = None,
) -> str:
    """Build the final LLM prompt for one agent invocation."""

    loaded_config = agent_config or load_agent_config(agent_dir)
    prompts = loaded_config.get("prompts", {})
    base_prompt_path = prompts.get("agent_prompt")
    if not base_prompt_path:
        raise ValueError("agent.yaml must define prompts.agent_prompt")

    base_prompt = read_text_file(resolve_agent_file(agent_dir, base_prompt_path))
    side_configs = load_agent_side_configs(agent_dir, loaded_config)

    prompt_payload = {
        "agent": loaded_config.get("agent", {}),
        "role": loaded_config.get("role", {}),
        "top_level_workflow_contract": loaded_config.get("top_level_workflow_contract", {}),
        "allowed_skills": loaded_config.get("allowed_skills", []),
        "allowed_mcp_tools": loaded_config.get("allowed_mcp_tools", []),
        "allowed_rag_resources": loaded_config.get("allowed_rag_resources", []),
        "skill_manifests": side_configs.get("skills", []),
        "mcp_config": side_configs.get("mcp", {}),
        "rag_config": side_configs.get("rag", {}),
        "memory_config": side_configs.get("memory", {}),
        "agent_input": agent_input,
        "result_schema_path": str(result_schema_path) if result_schema_path else None,
    }

    return "\n\n".join(
        [
            base_prompt,
            "## Runtime Agent Context",
            json.dumps(prompt_payload, ensure_ascii=False, indent=2, sort_keys=True),
        ]
    )


def build_runtime_config(
    agent_dir: str | Path,
    parent_workflow_step_id: str,
    agent_config: JsonObject | None = None,
    agent_type_override: str | None = None,
) -> AgentRuntimeConfig:
    """Create ``AgentRuntimeConfig`` from an agent folder and ``agent.yaml``."""

    loaded_config = agent_config or load_agent_config(agent_dir)
    agent_meta = loaded_config.get("agent", {})
    output_config = loaded_config.get("output", {})
    agent_type = agent_type_override or agent_meta.get("type", "normal")
    result_schema_key = (
        "evaluator_result_schema"
        if agent_type == "evaluator" and output_config.get("evaluator_result_schema")
        else "result_schema"
    )

    return AgentRuntimeConfig(
        agent_id=agent_meta.get("id", "UNKNOWN_AGENT_ID"),
        parent_workflow_step_id=parent_workflow_step_id,
        agent_type=agent_type,
        agent_output_schema_path=resolve_agent_file(
            agent_dir,
            output_config.get("schema", "schemas/agent_output.schema.json"),
        ),
        result_schema_path=resolve_agent_file(
            agent_dir,
            output_config.get(result_schema_key, "schemas/result.schema.json"),
        ),
        repair_prompt_path=resolve_agent_file(
            agent_dir,
            output_config.get("repair_prompt", "prompts/output_repair_prompt.md"),
        ),
        max_repair_attempts=int(output_config.get("max_repair_attempts", 2)),
        invalid_decision=output_config.get("invalid_decision", "iterate"),
    )
