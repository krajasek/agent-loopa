"""Documentation Agent — generates docstrings and README sections."""

from __future__ import annotations

from agent_loopa.agents.base import BaseAgent
from agent_loopa.models.artifacts import Documentation
from agent_loopa.models.messages import AgentInput, AgentOutput
from agent_loopa.models.verdicts import DocumentationVerdict, VerdictStatus


class DocumentationAgent(BaseAgent):
    name = "documentation"

    def _default_system_prompt(self) -> str:
        return (
            "You are a technical writer and senior developer. "
            "Generate comprehensive documentation for the provided code, including: "
            "inline docstrings (Google style for Python), type annotations where missing, "
            "and a README section covering usage, API reference, and examples.\n\n"
            "Respond with valid JSON in exactly this format:\n"
            "{\n"
            '  "inline_docs": "<complete file content with docstrings added>",\n'
            '  "readme_section": "<markdown README section>",\n'
            '  "has_docstrings": true,\n'
            '  "has_readme_section": true,\n'
            '  "confidence": 0.0-1.0,\n'
            '  "summary": "..."\n'
            "}"
        )

    async def run(self, input: AgentInput) -> AgentOutput:
        if not input.code:
            return AgentOutput(
                agent_name=self.name,
                iteration=input.iteration,
                doc_verdict=DocumentationVerdict(
                    status=VerdictStatus.WARNING,
                    confidence=0.5,
                    summary="No code provided for documentation.",
                ),
            )

        prompt = (
            f"Generate documentation for this {input.language} code:\n\n"
            f"```{input.language}\n{input.code.content}\n```\n\n"
            f"Module/file: {input.code.filename}\n"
            "Add Google-style docstrings to all public functions and classes. "
            "Also write a README section explaining what this code does and how to use it. "
            "Respond with JSON only."
        )
        raw, tokens = await self._call_llm(prompt)
        data = self._parse_json_response(raw)

        docs = Documentation(
            inline_docs=data.get("inline_docs", ""),
            readme_section=data.get("readme_section", ""),
            summary=data.get("summary", ""),
        )

        verdict = DocumentationVerdict(
            status=VerdictStatus.PASS,
            confidence=float(data.get("confidence", 0.8)),
            has_docstrings=bool(data.get("has_docstrings", True)),
            has_readme_section=bool(data.get("has_readme_section", True)),
            summary=data.get("summary", ""),
        )

        return AgentOutput(
            agent_name=self.name,
            iteration=input.iteration,
            documentation=docs,
            doc_verdict=verdict,
            raw_response=raw,
            tokens_used=tokens,
        )
