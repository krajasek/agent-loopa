"""Test Cases Agent — generates unit and functional tests."""

from __future__ import annotations

from agent_loopa.agents.base import BaseAgent
from agent_loopa.models.artifacts import TestFile, TestSuite
from agent_loopa.models.messages import AgentInput, AgentOutput
from agent_loopa.models.verdicts import Issue, TestVerdict, VerdictStatus


class TestCasesAgent(BaseAgent):
    name = "test_cases"

    def _default_system_prompt(self) -> str:
        return (
            "You are a senior test engineer. Write comprehensive test suites covering unit "
            "tests (individual functions/methods), functional tests (end-to-end flows), and "
            "edge cases. Use pytest for Python. Include fixtures and parametrize where appropriate.\n\n"
            "Respond with valid JSON in exactly this format:\n"
            "{\n"
            '  "test_files": [\n'
            '    {"filename": "test_<name>.py", "content": "...", "framework": "pytest"}\n'
            "  ],\n"
            '  "unit_test_count": 0,\n'
            '  "functional_test_count": 0,\n'
            '  "coverage_estimate": 0.0,\n'
            '  "summary": "..."\n'
            "}"
        )

    async def run(self, input: AgentInput) -> AgentOutput:
        if not input.code:
            return AgentOutput(
                agent_name=self.name,
                iteration=input.iteration,
                test_verdict=TestVerdict(
                    status=VerdictStatus.WARNING,
                    confidence=0.5,
                    summary="No code provided for test generation.",
                ),
            )

        prompt = (
            f"Write a comprehensive test suite for this {input.language} code:\n\n"
            f"```{input.language}\n{input.code.content}\n```\n\n"
            f"Filename being tested: {input.code.filename}\n"
            "Respond with JSON only."
        )
        raw, tokens = await self._call_llm(prompt)
        data = self._parse_json_response(raw)

        test_files = [
            TestFile(
                filename=tf.get("filename", "test_output.py"),
                content=tf.get("content", ""),
                framework=tf.get("framework", "pytest"),
            )
            for tf in data.get("test_files", [])
        ]

        suite = TestSuite(
            test_files=test_files,
            unit_test_count=data.get("unit_test_count", 0),
            functional_test_count=data.get("functional_test_count", 0),
            summary=data.get("summary", ""),
        )

        total = suite.unit_test_count + suite.functional_test_count
        coverage = float(data.get("coverage_estimate", 0.7))

        verdict = TestVerdict(
            status=VerdictStatus.PASS if test_files else VerdictStatus.FAIL,
            confidence=0.85 if test_files else 0.3,
            summary=data.get("summary", f"Generated {total} tests across {len(test_files)} file(s)."),
            unit_tests_pass=True,
            coverage_estimate=coverage,
        )

        return AgentOutput(
            agent_name=self.name,
            iteration=input.iteration,
            test_suite=suite,
            test_verdict=verdict,
            raw_response=raw,
            tokens_used=tokens,
        )
