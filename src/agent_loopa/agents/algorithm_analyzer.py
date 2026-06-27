"""Algorithm Analyzer Agent — time/space complexity analysis."""

from __future__ import annotations

from agent_loopa.agents.base import BaseAgent
from agent_loopa.models.artifacts import ComplexityAnalysis, ComplexityEntry
from agent_loopa.models.messages import AgentInput, AgentOutput
from agent_loopa.models.verdicts import ComplexityVerdict, Issue, VerdictStatus


class AlgorithmAnalyzerAgent(BaseAgent):
    name = "algorithm_analyzer"

    def _default_system_prompt(self) -> str:
        return (
            "You are an expert algorithms engineer specializing in computational complexity. "
            "Analyze the provided code for time and space complexity of each function. "
            "Identify inefficiencies and suggest improvements.\n\n"
            "Respond with valid JSON in exactly this format:\n"
            "{\n"
            '  "entries": [\n'
            '    {"function_name": "...", "time_complexity": "O(...)", "space_complexity": "O(...)", "notes": "..."}\n'
            "  ],\n"
            '  "overall_time": "O(...)",\n'
            '  "overall_space": "O(...)",\n'
            '  "acceptable": true,\n'
            '  "confidence": 0.85,\n'
            '  "issues": [{"description": "...", "suggestion": "..."}],\n'
            '  "summary": "..."\n'
            "}"
        )

    async def run(self, input: AgentInput) -> AgentOutput:
        if not input.code:
            return AgentOutput(
                agent_name=self.name,
                iteration=input.iteration,
                complexity_verdict=ComplexityVerdict(
                    status=VerdictStatus.WARNING,
                    confidence=0.5,
                    summary="No code provided for analysis.",
                ),
            )

        prompt = (
            f"Analyze the time and space complexity of this {input.language} code:\n\n"
            f"```{input.language}\n{input.code.content}\n```\n\n"
            "Respond with JSON only."
        )
        raw, tokens = await self._call_llm(prompt)
        data = self._parse_json_response(raw)

        entries = [
            ComplexityEntry(
                function_name=e.get("function_name", ""),
                time_complexity=e.get("time_complexity", "O(?)"),
                space_complexity=e.get("space_complexity", "O(?)"),
                notes=e.get("notes", ""),
            )
            for e in data.get("entries", [])
        ]

        analysis = ComplexityAnalysis(
            entries=entries,
            overall_time=data.get("overall_time", ""),
            overall_space=data.get("overall_space", ""),
            summary=data.get("summary", ""),
        )

        issues = [
            Issue(description=i.get("description", ""), suggestion=i.get("suggestion", ""))
            for i in data.get("issues", [])
        ]
        acceptable = data.get("acceptable", True)
        verdict = ComplexityVerdict(
            status=VerdictStatus.PASS if acceptable else VerdictStatus.FAIL,
            confidence=float(data.get("confidence", 0.7)),
            issues=issues,
            summary=data.get("summary", ""),
            acceptable_complexity=acceptable,
        )

        return AgentOutput(
            agent_name=self.name,
            iteration=input.iteration,
            complexity_analysis=analysis,
            complexity_verdict=verdict,
            raw_response=raw,
            tokens_used=tokens,
        )
