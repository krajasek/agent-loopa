"""Pipeline stage definitions and ordering."""

from __future__ import annotations

from enum import Enum


class PipelineStage(str, Enum):
    """Named pipeline stages in execution order."""

    CODER = "coder"
    ALGORITHM_ANALYZER = "algorithm_analyzer"
    CODE_REVIEWER = "code_reviewer"
    SECURITY = "security"
    TEST_CASES = "test_cases"
    DOCUMENTATION = "documentation"


# Stages that run in the iterative refinement loop
ITERATION_STAGES: list[PipelineStage] = [
    PipelineStage.CODER,
    PipelineStage.ALGORITHM_ANALYZER,
    PipelineStage.CODE_REVIEWER,
]

# Stages that run concurrently after the iteration loop passes
PARALLEL_STAGES: list[PipelineStage] = [
    PipelineStage.SECURITY,
    PipelineStage.TEST_CASES,
    PipelineStage.DOCUMENTATION,
]

# Full ordered list
ALL_STAGES: list[PipelineStage] = ITERATION_STAGES + PARALLEL_STAGES


def get_iteration_stages(skip: set[str] | None = None) -> list[PipelineStage]:
    """Return enabled iteration stages."""
    skip = skip or set()
    return [s for s in ITERATION_STAGES if s.value not in skip]


def get_parallel_stages(skip: set[str] | None = None) -> list[PipelineStage]:
    """Return enabled parallel stages."""
    skip = skip or set()
    return [s for s in PARALLEL_STAGES if s.value not in skip]
