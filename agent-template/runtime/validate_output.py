"""Validation helpers for the agent output contract gate.

This module is intentionally small and deterministic. It does not judge task
quality. It only checks whether model output is machine-readable JSON and
whether parsed objects match the configured JSON Schemas.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover - dependency guard for template use
    raise RuntimeError(
        "The agent runtime template requires the 'jsonschema' package. "
        "Install it with: pip install jsonschema"
    ) from exc


def load_json_file(path: str | Path) -> dict[str, Any]:
    """Load a JSON file from disk."""

    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object in schema file: {path}")
    return value


def parse_json_text(raw_text: str) -> tuple[dict[str, Any] | None, list[str]]:
    """Parse raw model text as a JSON object."""

    try:
        value = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return None, [f"Invalid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}"]

    if not isinstance(value, dict):
        return None, ["Parsed JSON must be an object."]

    return value, []


def validate_against_schema(instance: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Return JSON Schema validation errors as stable human-readable strings."""

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
    rendered: list[str] = []

    for error in errors:
        path = ".".join(str(part) for part in error.absolute_path)
        location = path if path else "$"
        rendered.append(f"{location}: {error.message}")

    return rendered


def validate_result(result: dict[str, Any], result_schema: dict[str, Any]) -> list[str]:
    """Validate the task-specific result payload."""

    return validate_against_schema(result, result_schema)


def validate_agent_output(
    agent_output: dict[str, Any],
    agent_output_schema: dict[str, Any],
) -> list[str]:
    """Validate the final orchestrator-facing agent output wrapper."""

    return validate_against_schema(agent_output, agent_output_schema)
