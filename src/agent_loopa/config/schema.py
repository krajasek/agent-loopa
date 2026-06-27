"""Configuration schemas for agent-loopa pipelines."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import tomli
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentConfig(BaseModel):
    """Per-agent configuration."""

    model: str = "claude-sonnet-4-6"
    max_tokens: int = 4096
    temperature: float = 0.2
    enabled: bool = True
    system_prompt: str | None = None


class QualityGateConfig(BaseModel):
    """Quality gate thresholds and agent classification."""

    blocking_agents: list[str] = Field(
        default_factory=lambda: ["security", "code_reviewer"]
    )
    advisory_agents: list[str] = Field(
        default_factory=lambda: ["algorithm_analyzer", "documentation"]
    )
    early_exit_confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    max_iterations: int = Field(default=3, ge=1, le=10)


class PipelineConfig(BaseModel):
    """Full pipeline configuration."""

    agents: dict[str, AgentConfig] = Field(default_factory=dict)
    gate: QualityGateConfig = Field(default_factory=QualityGateConfig)
    output_dir: str = "./output"
    audit_enabled: bool = True

    @model_validator(mode="before")
    @classmethod
    def _fill_default_agents(cls, data: Any) -> Any:
        if isinstance(data, dict):
            agents = data.get("agents", {})
            defaults = {
                "coder": {},
                "algorithm_analyzer": {},
                "code_reviewer": {},
                "security": {},
                "test_cases": {},
                "documentation": {},
            }
            for name, cfg in defaults.items():
                if name not in agents:
                    agents[name] = cfg
            data["agents"] = agents
        return data

    def get_agent(self, name: str) -> AgentConfig:
        return self.agents.get(name, AgentConfig())

    @classmethod
    def from_toml(cls, path: str | Path) -> "PipelineConfig":
        from agent_loopa.config.loader import load_config
        return load_config(path)


class AppSettings(BaseSettings):
    """Validates environment — at least one provider key must be set."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    mistral_api_key: str = ""
    azure_api_key: str = ""
    ollama_api_base: str = ""

    @model_validator(mode="after")
    def _at_least_one_provider(self) -> "AppSettings":
        keys = [
            self.openai_api_key,
            self.anthropic_api_key,
            self.gemini_api_key,
            self.mistral_api_key,
            self.azure_api_key,
            self.ollama_api_base,
        ]
        if not any(keys):
            raise ValueError(
                "No LLM provider API key found. "
                "Set at least one of OPENAI_API_KEY, ANTHROPIC_API_KEY, "
                "GEMINI_API_KEY, MISTRAL_API_KEY, AZURE_API_KEY, or OLLAMA_API_BASE "
                "in your environment or .env file."
            )
        return self
