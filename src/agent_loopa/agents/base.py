"""Abstract base class for all agents."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from agent_loopa.config.schema import AgentConfig
from agent_loopa.models.messages import AgentInput, AgentOutput
from agent_loopa.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Context-isolated LLM agent.

    Each instance maintains its own conversation history. The orchestrator
    passes only structured ``AgentInput`` objects — never raw outputs or
    prompts from other agents.
    """

    name: str = "base"

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self._messages: list[dict[str, str]] = []
        if config.system_prompt:
            self._messages.append({"role": "system", "content": config.system_prompt})
        else:
            self._messages.append({"role": "system", "content": self._default_system_prompt()})

    @abstractmethod
    def _default_system_prompt(self) -> str:
        """Return the default system prompt for this agent."""

    @abstractmethod
    async def run(self, input: AgentInput) -> AgentOutput:
        """Execute the agent and return a typed output envelope."""

    async def _call_llm(self, user_message: str) -> tuple[str, int]:
        """Send *user_message* and return (response_text, tokens_used).

        Appends the user turn and assistant reply to the conversation history
        so multi-turn context is preserved within a single iteration.
        """
        from litellm import acompletion

        self._messages.append({"role": "user", "content": user_message})

        async def _call() -> Any:
            return await acompletion(
                model=self.config.model,
                messages=self._messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

        response = await retry_with_backoff(
            _call,
            max_retries=2,
            base_delay=1.0,
        )

        text: str = response.choices[0].message.content or ""
        tokens: int = getattr(response.usage, "total_tokens", 0)

        self._messages.append({"role": "assistant", "content": text})
        return text, tokens

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """Extract JSON from an LLM response (handles markdown fences)."""
        text = text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.splitlines()
            # Drop opening fence (e.g. ```json)
            start = 1
            # Drop closing fence
            end = len(lines)
            for i in range(len(lines) - 1, 0, -1):
                if lines[i].strip() == "```":
                    end = i
                    break
            text = "\n".join(lines[start:end])

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning("Failed to parse JSON response: %s\nRaw text: %.200s", exc, text)
            return {}

    def reset_history(self) -> None:
        """Clear conversation history, keeping the system prompt."""
        system_msg = self._messages[0] if self._messages else None
        self._messages = [system_msg] if system_msg else []
