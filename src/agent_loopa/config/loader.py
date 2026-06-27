"""TOML config loader with .env resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import tomli

from agent_loopa.config.schema import AgentConfig, PipelineConfig, QualityGateConfig


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


_DEFAULTS: dict[str, Any] = {
    "agents": {
        "coder": {"model": "claude-sonnet-4-6", "max_tokens": 4096, "temperature": 0.2},
        "algorithm_analyzer": {"model": "claude-sonnet-4-6", "max_tokens": 2048, "temperature": 0.1},
        "code_reviewer": {"model": "claude-sonnet-4-6", "max_tokens": 2048, "temperature": 0.1},
        "security": {"model": "claude-sonnet-4-6", "max_tokens": 2048, "temperature": 0.1},
        "test_cases": {"model": "claude-sonnet-4-6", "max_tokens": 4096, "temperature": 0.3},
        "documentation": {"model": "claude-sonnet-4-6", "max_tokens": 2048, "temperature": 0.2},
    },
    "gate": {
        "blocking_agents": ["security", "code_reviewer"],
        "advisory_agents": ["algorithm_analyzer", "documentation"],
        "early_exit_confidence": 0.9,
        "max_iterations": 3,
    },
    "output_dir": "./output",
    "audit_enabled": True,
}


def load_config(path: str | Path) -> PipelineConfig:
    """Load a TOML pipeline config, merging with built-in defaults."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "rb") as f:
        raw = tomli.load(f)

    merged = _deep_merge(_DEFAULTS, raw)
    return PipelineConfig.model_validate(merged)


def default_config() -> PipelineConfig:
    """Return the built-in default pipeline config."""
    return PipelineConfig.model_validate(_DEFAULTS)
