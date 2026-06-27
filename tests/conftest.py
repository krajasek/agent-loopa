"""Shared pytest fixtures — mocks litellm so no real API calls are made."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_litellm_response(content: str) -> MagicMock:
    """Build a fake litellm ModelResponse."""
    choice = MagicMock()
    choice.message.content = content
    usage = MagicMock()
    usage.total_tokens = 42
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage
    return resp


# ── Agent response fixtures ────────────────────────────────────────────────

CODER_RESPONSE = json.dumps({
    "filename": "rate_limiter.py",
    "language": "python",
    "content": "class RateLimiter:\n    def __init__(self, rate):\n        self.rate = rate\n",
    "summary": "Implemented a basic rate limiter.",
})

ANALYZER_PASS_RESPONSE = json.dumps({
    "entries": [{"function_name": "__init__", "time_complexity": "O(1)", "space_complexity": "O(1)", "notes": ""}],
    "overall_time": "O(1)",
    "overall_space": "O(1)",
    "acceptable": True,
    "confidence": 0.92,
    "issues": [],
    "summary": "Complexity is acceptable.",
})

ANALYZER_FAIL_RESPONSE = json.dumps({
    "entries": [{"function_name": "check", "time_complexity": "O(n)", "space_complexity": "O(n)", "notes": "Linear scan"}],
    "overall_time": "O(n)",
    "overall_space": "O(n)",
    "acceptable": False,
    "confidence": 0.85,
    "issues": [{"description": "O(n) lookup — use dict for O(1)", "suggestion": "Use a dictionary"}],
    "summary": "O(n) lookup found, use dict for O(1).",
})

REVIEWER_PASS_RESPONSE = json.dumps({
    "status": "pass",
    "confidence": 0.93,
    "blocking_issues": [],
    "style_issues": [],
    "issues": [],
    "summary": "Code looks good.",
})

REVIEWER_FAIL_RESPONSE = json.dumps({
    "status": "fail",
    "confidence": 0.88,
    "blocking_issues": [{"description": "Missing thread-safety for concurrent use", "suggestion": "Add threading.Lock"}],
    "style_issues": [],
    "issues": [{"description": "Missing thread-safety for concurrent use", "suggestion": "Add threading.Lock"}],
    "summary": "Missing thread-safety for concurrent use.",
})

SECURITY_PASS_RESPONSE = json.dumps({
    "status": "pass",
    "confidence": 0.95,
    "findings": [],
    "owasp_categories_checked": ["A01:2021-Broken Access Control"],
    "summary": "No security findings.",
})

TEST_RESPONSE = json.dumps({
    "test_files": [
        {"filename": "test_rate_limiter.py", "content": "def test_init():\n    pass\n", "framework": "pytest"}
    ],
    "unit_test_count": 5,
    "functional_test_count": 2,
    "coverage_estimate": 0.85,
    "summary": "Generated 7 tests.",
})

DOC_RESPONSE = json.dumps({
    "inline_docs": "class RateLimiter:\n    \"\"\"Rate limiter.\"\"\"\n",
    "readme_section": "## RateLimiter\n\nA rate limiter implementation.",
    "has_docstrings": True,
    "has_readme_section": True,
    "confidence": 0.9,
    "summary": "Docstrings and README section generated.",
})


@pytest.fixture
def mock_litellm_pass():
    """Mock litellm.acompletion so all agents return passing responses."""
    response_map = {
        "coder": CODER_RESPONSE,
        "algorithm_analyzer": ANALYZER_PASS_RESPONSE,
        "code_reviewer": REVIEWER_PASS_RESPONSE,
        "security": SECURITY_PASS_RESPONSE,
        "test_cases": TEST_RESPONSE,
        "documentation": DOC_RESPONSE,
    }

    call_count = {"n": 0}
    responses = [
        CODER_RESPONSE,
        ANALYZER_PASS_RESPONSE,
        REVIEWER_PASS_RESPONSE,
        SECURITY_PASS_RESPONSE,
        TEST_RESPONSE,
        DOC_RESPONSE,
    ]

    async def _mock_acompletion(**kwargs: Any) -> MagicMock:
        idx = call_count["n"] % len(responses)
        call_count["n"] += 1
        return _make_litellm_response(responses[idx])

    with patch("litellm.acompletion", side_effect=_mock_acompletion):
        yield


@pytest.fixture
def mock_litellm_fail_then_pass():
    """Mock litellm.acompletion: first iteration fails gate, second passes."""
    # Pattern: coder → analyzer(fail) → reviewer(fail) → coder → analyzer(pass) → reviewer(pass)
    # then parallel: security, tests, docs
    responses = [
        CODER_RESPONSE,         # iter 1 coder
        ANALYZER_FAIL_RESPONSE, # iter 1 analyzer
        REVIEWER_FAIL_RESPONSE, # iter 1 reviewer
        CODER_RESPONSE,         # iter 2 coder
        ANALYZER_PASS_RESPONSE, # iter 2 analyzer
        REVIEWER_PASS_RESPONSE, # iter 2 reviewer
        SECURITY_PASS_RESPONSE, # parallel security
        TEST_RESPONSE,          # parallel tests
        DOC_RESPONSE,           # parallel docs
    ]

    call_count = {"n": 0}

    async def _mock_acompletion(**kwargs: Any) -> MagicMock:
        idx = min(call_count["n"], len(responses) - 1)
        call_count["n"] += 1
        return _make_litellm_response(responses[idx])

    with patch("litellm.acompletion", side_effect=_mock_acompletion):
        yield
