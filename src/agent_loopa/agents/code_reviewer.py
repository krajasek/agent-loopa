"""Code Reviewer Agent — correctness, style, and thread-safety review."""

from __future__ import annotations

from agent_loopa.agents.base import BaseAgent
from agent_loopa.models.messages import AgentInput, AgentOutput
from agent_loopa.models.verdicts import Issue, ReviewVerdict, VerdictStatus


class CodeReviewAgent(BaseAgent):
    name = "code_reviewer"

    def _default_system_prompt(self) -> str:
        return (
            "You are a senior software engineer performing a thorough code review. "
            "Evaluate the code for: correctness, edge cases, error handling, thread-safety, "
            "performance, readability, maintainability, and adherence to language idioms.\n\n"
            "Respond with valid JSON in exactly this format:\n"
            "{\n"
            '  "status": "pass" | "fail",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "blocking_issues": [{"description": "...", "line_number": null, "suggestion": "..."}],\n'
            '  "style_issues": [{"description": "...", "suggestion": "..."}],\n'
            '  "issues": [{"description": "...", "suggestion": "..."}],\n'
            '  "summary": "One or two sentence overall assessment"\n'
            "}\n\n"
            "blocking_issues are showstoppers that must be fixed before passing. "
            "style_issues are advisory improvements."
        )

    async def run(self, input: AgentInput) -> AgentOutput:
        if not input.code:
            return AgentOutput(
                agent_name=self.name,
                iteration=input.iteration,
                review_verdict=ReviewVerdict(
                    status=VerdictStatus.WARNING,
                    confidence=0.5,
                    summary="No code provided for review.",
                ),
            )

        prompt = (
            f"Review this {input.language} code:\n\n"
            f"```{input.language}\n{input.code.content}\n```\n\n"
            "Respond with JSON only."
        )
        raw, tokens = await self._call_llm(prompt)
        data = self._parse_json_response(raw)

        def _issues(key: str) -> list[Issue]:
            return [
                Issue(
                    description=i.get("description", ""),
                    line_number=i.get("line_number"),
                    suggestion=i.get("suggestion", ""),
                )
                for i in data.get(key, [])
            ]

        status_str = data.get("status", "fail").lower()
        status = VerdictStatus.PASS if status_str == "pass" else VerdictStatus.FAIL

        verdict = ReviewVerdict(
            status=status,
            confidence=float(data.get("confidence", 0.7)),
            issues=_issues("issues"),
            blocking_issues=_issues("blocking_issues"),
            style_issues=_issues("style_issues"),
            summary=data.get("summary", ""),
        )

        return AgentOutput(
            agent_name=self.name,
            iteration=input.iteration,
            review_verdict=verdict,
            raw_response=raw,
            tokens_used=tokens,
        )
