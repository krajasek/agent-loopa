"""Main orchestrator — runs the multi-agent pipeline."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from agent_loopa.agents.algorithm_analyzer import AlgorithmAnalyzerAgent
from agent_loopa.agents.code_reviewer import CodeReviewAgent
from agent_loopa.agents.coder import CoderAgent
from agent_loopa.agents.documentation import DocumentationAgent
from agent_loopa.agents.security import SecurityAgent
from agent_loopa.agents.test_cases import TestCasesAgent
from agent_loopa.audit.logger import AuditLogger
from agent_loopa.config.schema import PipelineConfig
from agent_loopa.models.artifacts import CodeArtifact, Documentation, TestSuite
from agent_loopa.models.audit import AuditEvent, AuditEventType
from agent_loopa.models.messages import AgentInput, AgentOutput
from agent_loopa.models.verdicts import BaseVerdict, SecurityReport
from agent_loopa.orchestrator.gate import QualityGate
from agent_loopa.orchestrator.pipeline import PipelineStage, get_iteration_stages, get_parallel_stages

logger = logging.getLogger(__name__)


class RunMode(str, Enum):
    GENERATE = "generate"
    REVIEW = "review"


@dataclass
class IterationRecord:
    iteration: int
    coder_output: AgentOutput | None = None
    analyzer_output: AgentOutput | None = None
    reviewer_output: AgentOutput | None = None
    gate_result: object = None  # GateResult


@dataclass
class OrchestratorResult:
    run_id: str
    mode: RunMode
    final_code: CodeArtifact | None
    test_suite: TestSuite | None
    documentation: Documentation | None
    security_report: SecurityReport | None
    iterations_run: int
    audit_log_path: Path | None
    iteration_records: list[IterationRecord] = field(default_factory=list)
    total_tokens: int = 0


class Orchestrator:
    """Runs the full agent pipeline for generate or review mode."""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self._gate = QualityGate(config.gate)

    async def run(
        self,
        mode: RunMode,
        task_description: str = "",
        language: str = "python",
        existing_files: list[CodeArtifact] | None = None,
        skip_agents: set[str] | None = None,
        on_agent_output: object = None,  # Optional callback: (AgentOutput) -> None
    ) -> OrchestratorResult:
        """Run the full pipeline.

        Args:
            mode: GENERATE (new code) or REVIEW (improve existing).
            task_description: Natural language task for GENERATE mode.
            language: Target programming language.
            existing_files: Source files for REVIEW mode.
            skip_agents: Set of agent names to disable for this run.
            on_agent_output: Optional async callback invoked after each agent completes.
        """
        run_id = str(uuid.uuid4())
        skip = skip_agents or set()
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        audit = AuditLogger(run_id=run_id, output_dir=output_dir, enabled=self.config.audit_enabled)

        await audit.log(AuditEvent(
            run_id=run_id,
            event_type=AuditEventType.RUN_START,
            data={"mode": mode.value, "language": language, "task": task_description},
        ))

        # Instantiate agents (fresh context per run)
        coder = CoderAgent(self.config.get_agent("coder"))
        analyzer = AlgorithmAnalyzerAgent(self.config.get_agent("algorithm_analyzer"))
        reviewer = CodeReviewAgent(self.config.get_agent("code_reviewer"))

        iteration_stages = get_iteration_stages(skip)
        parallel_stages = get_parallel_stages(skip)
        max_iter = self.config.gate.max_iterations

        current_code: CodeArtifact | None = None
        previous_verdicts: list[BaseVerdict] = []
        iteration_records: list[IterationRecord] = []
        total_tokens = 0
        gate_passed = False

        # ── Iteration loop ──────────────────────────────────────────────────
        for iteration in range(1, max_iter + 1):
            await audit.log(AuditEvent(
                run_id=run_id,
                event_type=AuditEventType.ITERATION_START,
                iteration=iteration,
            ))

            record = IterationRecord(iteration=iteration)
            agent_input = AgentInput(
                task_description=task_description,
                language=language,
                code=current_code,
                existing_files=existing_files or [],
                previous_verdicts=previous_verdicts,
                iteration=iteration,
                max_iterations=max_iter,
            )

            # Coder
            if PipelineStage.CODER in iteration_stages:
                await audit.log(AuditEvent(run_id=run_id, event_type=AuditEventType.AGENT_START, agent_name="coder", iteration=iteration))
                coder_out = await coder.run(agent_input)
                record.coder_output = coder_out
                total_tokens += coder_out.tokens_used
                current_code = coder_out.code
                await audit.log(AuditEvent(run_id=run_id, event_type=AuditEventType.AGENT_END, agent_name="coder", iteration=iteration, tokens_used=coder_out.tokens_used))
                if on_agent_output:
                    await _maybe_await(on_agent_output, coder_out)

            if current_code is None:
                logger.warning("No code artifact after coder — skipping iteration")
                break

            # Update input with current code
            agent_input = agent_input.model_copy(update={"code": current_code})

            # Algorithm Analyzer
            verdicts_this_iter: list[tuple[str, BaseVerdict]] = []
            if PipelineStage.ALGORITHM_ANALYZER in iteration_stages:
                await audit.log(AuditEvent(run_id=run_id, event_type=AuditEventType.AGENT_START, agent_name="algorithm_analyzer", iteration=iteration))
                analyzer_out = await analyzer.run(agent_input)
                record.analyzer_output = analyzer_out
                total_tokens += analyzer_out.tokens_used
                await audit.log(AuditEvent(run_id=run_id, event_type=AuditEventType.AGENT_END, agent_name="algorithm_analyzer", iteration=iteration, tokens_used=analyzer_out.tokens_used))
                if on_agent_output:
                    await _maybe_await(on_agent_output, analyzer_out)
                if analyzer_out.complexity_verdict:
                    verdicts_this_iter.append(("algorithm_analyzer", analyzer_out.complexity_verdict))

            # Code Reviewer
            if PipelineStage.CODE_REVIEWER in iteration_stages:
                await audit.log(AuditEvent(run_id=run_id, event_type=AuditEventType.AGENT_START, agent_name="code_reviewer", iteration=iteration))
                reviewer_out = await reviewer.run(agent_input)
                record.reviewer_output = reviewer_out
                total_tokens += reviewer_out.tokens_used
                await audit.log(AuditEvent(run_id=run_id, event_type=AuditEventType.AGENT_END, agent_name="code_reviewer", iteration=iteration, tokens_used=reviewer_out.tokens_used))
                if on_agent_output:
                    await _maybe_await(on_agent_output, reviewer_out)
                if reviewer_out.review_verdict:
                    verdicts_this_iter.append(("code_reviewer", reviewer_out.review_verdict))

            # Evaluate gate
            gate_result = self._gate.evaluate(verdicts_this_iter, iteration=iteration)
            record.gate_result = gate_result
            await audit.log(AuditEvent(
                run_id=run_id,
                event_type=AuditEventType.GATE_EVALUATED,
                iteration=iteration,
                data={"all_pass": gate_result.all_blocking_pass, "reason": gate_result.reason, "early_exit": gate_result.early_exit},
            ))

            # Build feedback verdicts for next iteration
            previous_verdicts = [v for _, v in verdicts_this_iter]

            await audit.log(AuditEvent(run_id=run_id, event_type=AuditEventType.ITERATION_END, iteration=iteration))
            iteration_records.append(record)

            if gate_result.all_blocking_pass:
                gate_passed = True
                logger.info("Gate passed on iteration %d: %s", iteration, gate_result.reason)
                break

            logger.info("Iteration %d gate failed: %s", iteration, gate_result.reason)

        iterations_run = len(iteration_records)

        # ── Parallel phase ───────────────────────────────────────────────────
        security_report: SecurityReport | None = None
        test_suite: TestSuite | None = None
        documentation: Documentation | None = None

        if current_code and parallel_stages:
            await audit.log(AuditEvent(run_id=run_id, event_type=AuditEventType.PARALLEL_PHASE_START))
            parallel_input = AgentInput(
                task_description=task_description,
                language=language,
                code=current_code,
                iteration=iterations_run,
                max_iterations=max_iter,
            )

            tasks = {}
            if PipelineStage.SECURITY in parallel_stages:
                tasks["security"] = SecurityAgent(self.config.get_agent("security")).run(parallel_input)
            if PipelineStage.TEST_CASES in parallel_stages:
                tasks["test_cases"] = TestCasesAgent(self.config.get_agent("test_cases")).run(parallel_input)
            if PipelineStage.DOCUMENTATION in parallel_stages:
                tasks["documentation"] = DocumentationAgent(self.config.get_agent("documentation")).run(parallel_input)

            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for (agent_name, _), result in zip(tasks.items(), results):
                if isinstance(result, Exception):
                    logger.error("Parallel agent %s failed: %s", agent_name, result)
                    continue
                out: AgentOutput = result
                total_tokens += out.tokens_used
                if on_agent_output:
                    await _maybe_await(on_agent_output, out)
                if agent_name == "security":
                    security_report = out.security_report
                elif agent_name == "test_cases":
                    test_suite = out.test_suite
                elif agent_name == "documentation":
                    documentation = out.documentation

            await audit.log(AuditEvent(run_id=run_id, event_type=AuditEventType.PARALLEL_PHASE_END, tokens_used=total_tokens))

        await audit.log(AuditEvent(
            run_id=run_id,
            event_type=AuditEventType.RUN_END,
            tokens_used=total_tokens,
            data={"iterations_run": iterations_run, "gate_passed": gate_passed},
        ))

        return OrchestratorResult(
            run_id=run_id,
            mode=mode,
            final_code=current_code,
            test_suite=test_suite,
            documentation=documentation,
            security_report=security_report,
            iterations_run=iterations_run,
            audit_log_path=audit.log_path,
            iteration_records=iteration_records,
            total_tokens=total_tokens,
        )


async def _maybe_await(fn: object, *args: object) -> None:
    import inspect
    if inspect.iscoroutinefunction(fn):
        await fn(*args)  # type: ignore[operator]
    else:
        fn(*args)  # type: ignore[operator]
