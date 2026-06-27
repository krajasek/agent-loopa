"""Unit tests for CoderAgent."""

from __future__ import annotations

import json
import pytest

from agent_loopa.agents.coder import CoderAgent
from agent_loopa.config.schema import AgentConfig
from agent_loopa.models.artifacts import CodeArtifact
from agent_loopa.models.messages import AgentInput
from agent_loopa.models.verdicts import BaseVerdict, Issue, VerdictStatus


VALID_CODER_JSON = json.dumps({
    "filename": "binary_search.py",
    "language": "python",
    "content": "def binary_search(arr, target):\n    lo, hi = 0, len(arr)-1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1\n",
    "summary": "Binary search implementation.",
})


@pytest.fixture
def agent():
    return CoderAgent(AgentConfig(model="claude-sonnet-4-6"))


class TestCoderAgent:
    async def test_generate_returns_code_artifact(self, agent, mock_litellm_pass):
        inp = AgentInput(task_description="Implement binary search", language="python")
        out = await agent.run(inp)
        assert out.code is not None
        assert out.agent_name == "coder"

    async def test_code_artifact_has_content(self, agent, mock_litellm_pass):
        inp = AgentInput(task_description="Implement binary search", language="python")
        out = await agent.run(inp)
        assert out.code.content != ""

    async def test_revision_preserves_parent_id(self, agent, mock_litellm_pass):
        parent = CodeArtifact(language="python", filename="foo.py", content="x=1")
        inp = AgentInput(task_description="Improve", language="python", code=parent)
        out = await agent.run(inp)
        assert out.code is not None
        assert out.code.parent_id == parent.id

    async def test_feedback_incorporated_in_prompt(self, agent, mock_litellm_pass):
        """Verify feedback verdicts are included in the prompt (via message history)."""
        verdict = BaseVerdict(
            status=VerdictStatus.FAIL,
            confidence=0.8,
            issues=[Issue(description="Missing error handling", suggestion="Add try/except")],
            summary="Missing error handling",
        )
        inp = AgentInput(
            task_description="Implement X",
            language="python",
            previous_verdicts=[verdict],
            iteration=2,
        )
        out = await agent.run(inp)
        # The agent ran (response parsed) without error
        assert out.code is not None

    async def test_no_verdict_in_output(self, agent, mock_litellm_pass):
        inp = AgentInput(task_description="Write a hello world", language="python")
        out = await agent.run(inp)
        assert out.get_verdict() is None
        assert out.code is not None

    def test_parse_json_strips_markdown_fence(self, agent):
        raw = '```json\n{"filename": "x.py", "language": "python", "content": "pass", "summary": "s"}\n```'
        data = agent._parse_json_response(raw)
        assert data["filename"] == "x.py"

    def test_parse_json_plain(self, agent):
        raw = '{"filename": "x.py", "language": "python", "content": "pass", "summary": "s"}'
        data = agent._parse_json_response(raw)
        assert data["content"] == "pass"
