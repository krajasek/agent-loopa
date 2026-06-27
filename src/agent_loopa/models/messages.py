"""Typed message envelopes passed between orchestrator and agents."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agent_loopa.models.artifacts import (
    CodeArtifact,
    ComplexityAnalysis,
    Documentation,
    TestSuite,
)
from agent_loopa.models.verdicts import (
    BaseVerdict,
    ComplexityVerdict,
    DocumentationVerdict,
    ReviewVerdict,
    SecurityReport,
    TestVerdict,
)


class AgentInput(BaseModel):
    """Typed input envelope — each agent selects the fields it needs."""

    # Task description (generate mode)
    task_description: str = ""
    language: str = "python"

    # Code to work with (review mode or subsequent iterations)
    code: CodeArtifact | None = None

    # Existing files (review mode)
    existing_files: list[CodeArtifact] = Field(default_factory=list)

    # Feedback from previous iteration
    previous_verdicts: list[BaseVerdict] = Field(default_factory=list)
    iteration: int = 1
    max_iterations: int = 3


class AgentOutput(BaseModel):
    """Typed output envelope — exactly one output field populated per agent."""

    agent_name: str
    iteration: int = 1

    # Coder
    code: CodeArtifact | None = None

    # AlgorithmAnalyzer
    complexity_analysis: ComplexityAnalysis | None = None
    complexity_verdict: ComplexityVerdict | None = None

    # CodeReviewer
    review_verdict: ReviewVerdict | None = None

    # Security
    security_report: SecurityReport | None = None

    # TestCases
    test_suite: TestSuite | None = None
    test_verdict: TestVerdict | None = None

    # Documentation
    documentation: Documentation | None = None
    doc_verdict: DocumentationVerdict | None = None

    # Raw LLM response for debugging
    raw_response: str = ""
    tokens_used: int = 0

    def get_verdict(self) -> BaseVerdict | None:
        """Return whichever verdict this output contains."""
        return (
            self.complexity_verdict
            or self.review_verdict
            or self.security_report
            or self.test_verdict
            or self.doc_verdict
        )
