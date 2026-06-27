"""Integration test: full generate pipeline with mocked litellm."""

from __future__ import annotations

import pytest

from agent_loopa.config.loader import default_config
from agent_loopa.models.verdicts import VerdictStatus
from agent_loopa.orchestrator.orchestrator import Orchestrator, RunMode


class TestGenerateFlow:
    async def test_full_pipeline_pass_first_iteration(self, mock_litellm_pass, tmp_path):
        cfg = default_config()
        cfg = cfg.model_copy(update={"output_dir": str(tmp_path)})
        orch = Orchestrator(config=cfg)

        result = await orch.run(
            mode=RunMode.GENERATE,
            task_description="Implement a rate limiter using the token bucket algorithm",
            language="python",
        )

        assert result.final_code is not None
        assert result.final_code.content != ""
        assert result.iterations_run >= 1
        assert result.test_suite is not None
        assert result.documentation is not None
        assert result.security_report is not None

    async def test_pipeline_iterates_on_gate_failure(self, mock_litellm_fail_then_pass, tmp_path):
        cfg = default_config()
        cfg = cfg.model_copy(update={
            "output_dir": str(tmp_path),
            "gate": cfg.gate.model_copy(update={"max_iterations": 3}),
        })
        orch = Orchestrator(config=cfg)

        result = await orch.run(
            mode=RunMode.GENERATE,
            task_description="Implement a rate limiter",
            language="python",
        )

        # Should have run at least 2 iterations (fail then pass)
        assert result.iterations_run >= 2
        assert result.final_code is not None

    async def test_audit_log_created(self, mock_litellm_pass, tmp_path):
        cfg = default_config()
        cfg = cfg.model_copy(update={"output_dir": str(tmp_path), "audit_enabled": True})
        orch = Orchestrator(config=cfg)

        result = await orch.run(
            mode=RunMode.GENERATE,
            task_description="Write a hello world function",
            language="python",
        )

        assert result.audit_log_path is not None
        assert result.audit_log_path.exists()
        content = result.audit_log_path.read_text()
        assert "run_start" in content
        assert "run_end" in content

    async def test_skip_agents(self, mock_litellm_pass, tmp_path):
        cfg = default_config()
        cfg = cfg.model_copy(update={"output_dir": str(tmp_path)})
        orch = Orchestrator(config=cfg)

        result = await orch.run(
            mode=RunMode.GENERATE,
            task_description="Write a fibonacci function",
            language="python",
            skip_agents={"documentation"},
        )

        # Documentation was skipped
        assert result.documentation is None
        # But code should still be produced
        assert result.final_code is not None

    async def test_total_tokens_tracked(self, mock_litellm_pass, tmp_path):
        cfg = default_config()
        cfg = cfg.model_copy(update={"output_dir": str(tmp_path)})
        orch = Orchestrator(config=cfg)

        result = await orch.run(
            mode=RunMode.GENERATE,
            task_description="Write a sort function",
            language="python",
        )

        assert result.total_tokens > 0

    async def test_on_agent_output_callback(self, mock_litellm_pass, tmp_path):
        cfg = default_config()
        cfg = cfg.model_copy(update={"output_dir": str(tmp_path)})
        orch = Orchestrator(config=cfg)

        seen_agents: list[str] = []

        async def callback(out):
            seen_agents.append(out.agent_name)

        await orch.run(
            mode=RunMode.GENERATE,
            task_description="Write a hash map",
            language="python",
            on_agent_output=callback,
        )

        assert "coder" in seen_agents
        assert "code_reviewer" in seen_agents
