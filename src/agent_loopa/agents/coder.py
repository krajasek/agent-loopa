"""Coder Agent — generates and refines code."""

from __future__ import annotations

import json

from agent_loopa.agents.base import BaseAgent
from agent_loopa.models.artifacts import CodeArtifact
from agent_loopa.models.messages import AgentInput, AgentOutput
from agent_loopa.models.verdicts import VerdictStatus


class CoderAgent(BaseAgent):
    name = "coder"

    def _default_system_prompt(self) -> str:
        return (
            "You are an expert software engineer. Your job is to write clean, correct, "
            "production-quality code. When given a task, produce complete, runnable code. "
            "When given feedback from reviewers, revise your code to address all issues.\n\n"
            "Always respond with valid JSON in exactly this format:\n"
            "{\n"
            '  "filename": "<filename with extension>",\n'
            '  "language": "<language>",\n'
            '  "content": "<complete file content>",\n'
            '  "summary": "<1-2 sentence description of what was written/changed>"\n'
            "}"
        )

    async def run(self, input: AgentInput) -> AgentOutput:
        prompt = self._build_prompt(input)
        raw, tokens = await self._call_llm(prompt)
        data = self._parse_json_response(raw)

        parent_id = input.code.id if input.code else None
        artifact = CodeArtifact(
            parent_id=parent_id,
            language=data.get("language", input.language),
            filename=data.get("filename", f"output.{input.language}"),
            content=data.get("content", ""),
        )

        return AgentOutput(
            agent_name=self.name,
            iteration=input.iteration,
            code=artifact,
            raw_response=raw,
            tokens_used=tokens,
        )

    def _build_prompt(self, input: AgentInput) -> str:
        parts: list[str] = []

        if input.code:
            parts.append(f"# Current code ({input.code.filename})\n\n```{input.language}\n{input.code.content}\n```")
        elif input.existing_files:
            file_blocks = "\n\n".join(
                f"## {f.filename}\n```{input.language}\n{f.content}\n```"
                for f in input.existing_files
            )
            parts.append(f"# Existing files to improve\n\n{file_blocks}")
        else:
            parts.append(f"# Task\n\n{input.task_description}\nLanguage: {input.language}")

        if input.previous_verdicts:
            feedback_lines: list[str] = []
            for v in input.previous_verdicts:
                status = v.status.value.upper()
                feedback_lines.append(f"[{status}] {v.summary}")
                for issue in v.issues:
                    feedback_lines.append(f"  - {issue.description}" + (f" → {issue.suggestion}" if issue.suggestion else ""))
            parts.append("# Feedback to address\n\n" + "\n".join(feedback_lines))

        parts.append(
            f"Iteration {input.iteration}/{input.max_iterations}. "
            "Produce complete, correct code addressing all feedback above. "
            "Respond with JSON only."
        )
        return "\n\n".join(parts)
