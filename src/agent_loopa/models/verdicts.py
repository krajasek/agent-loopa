"""Verdict models returned by each agent."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class VerdictStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


class SecuritySeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Issue(BaseModel):
    code: str = ""
    description: str
    line_number: int | None = None
    suggestion: str = ""


class BaseVerdict(BaseModel):
    status: VerdictStatus
    confidence: float = Field(ge=0.0, le=1.0)
    issues: list[Issue] = Field(default_factory=list)
    summary: str = ""

    @property
    def is_acceptable(self) -> bool:
        return self.status in (VerdictStatus.PASS, VerdictStatus.WARNING)


class ReviewVerdict(BaseVerdict):
    blocking_issues: list[Issue] = Field(default_factory=list)
    style_issues: list[Issue] = Field(default_factory=list)


class SecurityFinding(BaseModel):
    severity: SecuritySeverity
    owasp_category: str = ""
    description: str
    location: str = ""
    recommendation: str = ""


class SecurityReport(BaseVerdict):
    findings: list[SecurityFinding] = Field(default_factory=list)
    owasp_categories_checked: list[str] = Field(default_factory=list)


class ComplexityVerdict(BaseVerdict):
    """Verdict from AlgorithmAnalyzerAgent."""

    acceptable_complexity: bool = True


class TestVerdict(BaseVerdict):
    unit_tests_pass: bool = True
    coverage_estimate: float = 0.0


class DocumentationVerdict(BaseVerdict):
    has_docstrings: bool = False
    has_readme_section: bool = False
