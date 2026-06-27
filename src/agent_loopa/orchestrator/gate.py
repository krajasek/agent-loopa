"""Quality gate — evaluates agent verdicts and decides iteration vs proceed."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_loopa.config.schema import QualityGateConfig
from agent_loopa.models.verdicts import BaseVerdict, VerdictStatus


@dataclass
class GateResult:
    all_blocking_pass: bool
    should_iterate: bool
    blocking_failures: list[tuple[str, BaseVerdict]] = field(default_factory=list)
    advisory_warnings: list[tuple[str, BaseVerdict]] = field(default_factory=list)
    early_exit: bool = False
    reason: str = ""


class QualityGate:
    """Evaluates a set of named verdicts against gate configuration."""

    def __init__(self, config: QualityGateConfig) -> None:
        self.config = config

    def evaluate(
        self,
        named_verdicts: list[tuple[str, BaseVerdict]],
        iteration: int = 1,
    ) -> GateResult:
        """Evaluate verdicts and return a GateResult.

        Args:
            named_verdicts: List of (agent_name, verdict) pairs.
            iteration: Current iteration number (1-based).

        Returns:
            GateResult with pass/fail decision and detailed breakdown.
        """
        blocking_failures: list[tuple[str, BaseVerdict]] = []
        advisory_warnings: list[tuple[str, BaseVerdict]] = []
        blocking_verdicts: list[tuple[str, BaseVerdict]] = []

        verdict_map = {name: verdict for name, verdict in named_verdicts}

        for agent_name in self.config.blocking_agents:
            verdict = verdict_map.get(agent_name)
            if verdict is None:
                continue
            blocking_verdicts.append((agent_name, verdict))
            if not verdict.is_acceptable:
                blocking_failures.append((agent_name, verdict))

        for agent_name in self.config.advisory_agents:
            verdict = verdict_map.get(agent_name)
            if verdict is None:
                continue
            if not verdict.is_acceptable:
                advisory_warnings.append((agent_name, verdict))

        all_blocking_pass = len(blocking_failures) == 0

        # Early exit: all blocking agents have high confidence pass
        early_exit = all_blocking_pass and all(
            v.confidence >= self.config.early_exit_confidence
            for _, v in blocking_verdicts
        )

        # Should iterate if there are failures and we haven't hit max iterations
        should_iterate = (not all_blocking_pass) and (iteration < self.config.max_iterations)

        if early_exit:
            reason = f"All blocking agents passed with confidence ≥ {self.config.early_exit_confidence}"
        elif all_blocking_pass:
            reason = "All blocking agents passed"
        else:
            names = ", ".join(n for n, _ in blocking_failures)
            reason = f"Blocking failures from: {names}"

        return GateResult(
            all_blocking_pass=all_blocking_pass,
            should_iterate=should_iterate,
            blocking_failures=blocking_failures,
            advisory_warnings=advisory_warnings,
            early_exit=early_exit,
            reason=reason,
        )
