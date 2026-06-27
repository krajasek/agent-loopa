"""Unit tests for QualityGate."""

from __future__ import annotations

import pytest

from agent_loopa.config.schema import QualityGateConfig
from agent_loopa.models.verdicts import BaseVerdict, ReviewVerdict, SecurityReport, VerdictStatus
from agent_loopa.orchestrator.gate import QualityGate


def _cfg(**kwargs) -> QualityGateConfig:
    defaults = {
        "blocking_agents": ["security", "code_reviewer"],
        "advisory_agents": ["algorithm_analyzer"],
        "early_exit_confidence": 0.9,
        "max_iterations": 3,
    }
    defaults.update(kwargs)
    return QualityGateConfig(**defaults)


def _pass_verdict(confidence: float = 0.95) -> BaseVerdict:
    return BaseVerdict(status=VerdictStatus.PASS, confidence=confidence)


def _fail_verdict(confidence: float = 0.8) -> BaseVerdict:
    return BaseVerdict(status=VerdictStatus.FAIL, confidence=confidence)


class TestQualityGate:
    def test_all_blocking_pass(self):
        gate = QualityGate(_cfg())
        result = gate.evaluate([
            ("security", _pass_verdict(0.95)),
            ("code_reviewer", _pass_verdict(0.92)),
        ])
        assert result.all_blocking_pass is True
        assert result.should_iterate is False

    def test_blocking_failure_triggers_iterate(self):
        gate = QualityGate(_cfg())
        result = gate.evaluate([
            ("security", _pass_verdict()),
            ("code_reviewer", _fail_verdict()),
        ], iteration=1)
        assert result.all_blocking_pass is False
        assert result.should_iterate is True
        assert len(result.blocking_failures) == 1
        assert result.blocking_failures[0][0] == "code_reviewer"

    def test_no_iterate_at_max_iterations(self):
        gate = QualityGate(_cfg(max_iterations=3))
        result = gate.evaluate([
            ("security", _fail_verdict()),
        ], iteration=3)
        assert result.all_blocking_pass is False
        assert result.should_iterate is False  # at max — don't iterate

    def test_early_exit_on_high_confidence(self):
        gate = QualityGate(_cfg(early_exit_confidence=0.9))
        result = gate.evaluate([
            ("security", _pass_verdict(0.97)),
            ("code_reviewer", _pass_verdict(0.95)),
        ])
        assert result.early_exit is True
        assert result.all_blocking_pass is True

    def test_no_early_exit_if_confidence_below_threshold(self):
        gate = QualityGate(_cfg(early_exit_confidence=0.9))
        result = gate.evaluate([
            ("security", _pass_verdict(0.95)),
            ("code_reviewer", _pass_verdict(0.85)),  # below threshold
        ])
        assert result.early_exit is False
        assert result.all_blocking_pass is True

    def test_advisory_failures_dont_block(self):
        gate = QualityGate(_cfg())
        result = gate.evaluate([
            ("security", _pass_verdict()),
            ("code_reviewer", _pass_verdict()),
            ("algorithm_analyzer", _fail_verdict()),  # advisory only
        ])
        assert result.all_blocking_pass is True
        assert len(result.advisory_warnings) == 1

    def test_missing_blocking_agent_verdict_is_ignored(self):
        gate = QualityGate(_cfg())
        # Only one of two blocking agents present
        result = gate.evaluate([
            ("security", _pass_verdict()),
            # code_reviewer missing
        ])
        assert result.all_blocking_pass is True  # no failure recorded

    def test_both_blocking_fail(self):
        gate = QualityGate(_cfg())
        result = gate.evaluate([
            ("security", _fail_verdict()),
            ("code_reviewer", _fail_verdict()),
        ], iteration=1)
        assert result.all_blocking_pass is False
        assert len(result.blocking_failures) == 2
