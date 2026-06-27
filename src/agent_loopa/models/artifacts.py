"""Output artifacts produced by agents."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class CodeArtifact(BaseModel):
    """A versioned code artifact with lineage tracking."""

    id: str = Field(default_factory=_new_id)
    parent_id: str | None = None
    language: str
    filename: str
    content: str
    line_count: int = 0
    created_at: datetime = Field(default_factory=_now)

    def model_post_init(self, __context: object) -> None:
        if self.line_count == 0 and self.content:
            object.__setattr__(self, "line_count", len(self.content.splitlines()))


class TestFile(BaseModel):
    filename: str
    content: str
    framework: str = "pytest"


class TestSuite(BaseModel):
    """Collection of generated test files."""

    id: str = Field(default_factory=_new_id)
    test_files: list[TestFile] = Field(default_factory=list)
    unit_test_count: int = 0
    functional_test_count: int = 0
    summary: str = ""


class Documentation(BaseModel):
    """Generated documentation artifact."""

    id: str = Field(default_factory=_new_id)
    inline_docs: str = ""
    readme_section: str = ""
    summary: str = ""


class ComplexityEntry(BaseModel):
    function_name: str
    time_complexity: str
    space_complexity: str
    notes: str = ""


class ComplexityAnalysis(BaseModel):
    """Algorithm complexity analysis results."""

    id: str = Field(default_factory=_new_id)
    entries: list[ComplexityEntry] = Field(default_factory=list)
    overall_time: str = ""
    overall_space: str = ""
    summary: str = ""
