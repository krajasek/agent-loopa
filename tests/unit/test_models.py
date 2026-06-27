"""Unit tests for Pydantic models."""

from __future__ import annotations

import pytest

from agent_loopa.models.artifacts import CodeArtifact, ComplexityAnalysis, TestSuite
from agent_loopa.models.messages import AgentInput, AgentOutput
from agent_loopa.models.verdicts import (
    BaseVerdict,
    Issue,
    ReviewVerdict,
    SecurityFinding,
    SecurityReport,
    SecuritySeverity,
    VerdictStatus,
)


class TestCodeArtifact:
    def test_line_count_auto_computed(self):
        art = CodeArtifact(language="python", filename="foo.py", content="a\nb\nc\n")
        assert art.line_count == 3

    def test_parent_lineage(self):
        parent = CodeArtifact(language="python", filename="foo.py", content="x=1")
        child = CodeArtifact(language="python", filename="foo.py", content="x=2", parent_id=parent.id)
        assert child.parent_id == parent.id

    def test_unique_ids(self):
        a = CodeArtifact(language="python", filename="a.py", content="")
        b = CodeArtifact(language="python", filename="b.py", content="")
        assert a.id != b.id


class TestBaseVerdict:
    def test_pass_is_acceptable(self):
        v = BaseVerdict(status=VerdictStatus.PASS, confidence=0.9)
        assert v.is_acceptable is True

    def test_warning_is_acceptable(self):
        v = BaseVerdict(status=VerdictStatus.WARNING, confidence=0.5)
        assert v.is_acceptable is True

    def test_fail_not_acceptable(self):
        v = BaseVerdict(status=VerdictStatus.FAIL, confidence=0.8)
        assert v.is_acceptable is False

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            BaseVerdict(status=VerdictStatus.PASS, confidence=1.5)
        with pytest.raises(Exception):
            BaseVerdict(status=VerdictStatus.PASS, confidence=-0.1)


class TestReviewVerdict:
    def test_blocking_and_style_issues(self):
        v = ReviewVerdict(
            status=VerdictStatus.FAIL,
            confidence=0.8,
            blocking_issues=[Issue(description="Thread-safety missing")],
            style_issues=[Issue(description="Use snake_case")],
        )
        assert len(v.blocking_issues) == 1
        assert len(v.style_issues) == 1
        assert v.is_acceptable is False


class TestSecurityReport:
    def test_high_severity_finding(self):
        finding = SecurityFinding(
            severity=SecuritySeverity.HIGH,
            description="SQL injection",
            recommendation="Use parameterized queries",
        )
        report = SecurityReport(
            status=VerdictStatus.FAIL,
            confidence=0.95,
            findings=[finding],
        )
        assert report.findings[0].severity == SecuritySeverity.HIGH

    def test_empty_findings_pass(self):
        report = SecurityReport(status=VerdictStatus.PASS, confidence=0.98)
        assert report.is_acceptable is True


class TestAgentInput:
    def test_defaults(self):
        inp = AgentInput(task_description="Write a sort function")
        assert inp.language == "python"
        assert inp.iteration == 1
        assert inp.previous_verdicts == []

    def test_with_code(self):
        art = CodeArtifact(language="python", filename="sort.py", content="def sort(): pass")
        inp = AgentInput(task_description="Improve", code=art)
        assert inp.code is not None
        assert inp.code.filename == "sort.py"


class TestAgentOutput:
    def test_get_verdict_returns_review_verdict(self):
        rv = ReviewVerdict(status=VerdictStatus.PASS, confidence=0.9)
        out = AgentOutput(agent_name="code_reviewer", review_verdict=rv)
        assert out.get_verdict() is rv

    def test_get_verdict_returns_none_for_coder(self):
        art = CodeArtifact(language="python", filename="f.py", content="x=1")
        out = AgentOutput(agent_name="coder", code=art)
        assert out.get_verdict() is None
