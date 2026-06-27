"""Unit tests for pipeline stage ordering."""

from __future__ import annotations

import pytest

from agent_loopa.orchestrator.pipeline import (
    ALL_STAGES,
    ITERATION_STAGES,
    PARALLEL_STAGES,
    PipelineStage,
    get_iteration_stages,
    get_parallel_stages,
)


class TestPipelineStages:
    def test_iteration_stages_order(self):
        assert ITERATION_STAGES == [
            PipelineStage.CODER,
            PipelineStage.ALGORITHM_ANALYZER,
            PipelineStage.CODE_REVIEWER,
        ]

    def test_parallel_stages(self):
        assert set(PARALLEL_STAGES) == {
            PipelineStage.SECURITY,
            PipelineStage.TEST_CASES,
            PipelineStage.DOCUMENTATION,
        }

    def test_all_stages_includes_both(self):
        assert set(ALL_STAGES) == set(ITERATION_STAGES) | set(PARALLEL_STAGES)

    def test_get_iteration_stages_no_skip(self):
        stages = get_iteration_stages()
        assert stages == ITERATION_STAGES

    def test_get_iteration_stages_with_skip(self):
        stages = get_iteration_stages(skip={"algorithm_analyzer"})
        assert PipelineStage.ALGORITHM_ANALYZER not in stages
        assert PipelineStage.CODER in stages
        assert PipelineStage.CODE_REVIEWER in stages

    def test_get_parallel_stages_no_skip(self):
        stages = get_parallel_stages()
        assert set(stages) == {PipelineStage.SECURITY, PipelineStage.TEST_CASES, PipelineStage.DOCUMENTATION}

    def test_get_parallel_stages_skip_documentation(self):
        stages = get_parallel_stages(skip={"documentation"})
        assert PipelineStage.DOCUMENTATION not in stages
        assert PipelineStage.SECURITY in stages
        assert PipelineStage.TEST_CASES in stages

    def test_stage_values_are_strings(self):
        for stage in PipelineStage:
            assert isinstance(stage.value, str)
            assert stage.value == stage.value.lower()
