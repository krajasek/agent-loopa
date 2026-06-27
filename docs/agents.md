# Agents Reference

## Agent Contracts

All agents implement `BaseAgent` and follow this contract:
- **Input**: `AgentInput` — only fields relevant to the agent are used
- **Output**: `AgentOutput` — exactly one primary output field is populated
- **Context isolation**: own conversation history, no cross-agent visibility
- **Response format**: structured JSON (defined in system prompt)

---

## Coder Agent

**Role**: Generates new code from a task description, or refines existing code based on reviewer feedback.

**Input fields used**: `task_description`, `language`, `code` (previous version), `existing_files`, `previous_verdicts`, `iteration`

**Output**: `AgentOutput.code: CodeArtifact`

**System prompt contract**:
```json
{
  "filename": "<filename with extension>",
  "language": "<language>",
  "content": "<complete file content>",
  "summary": "<1-2 sentence description>"
}
```

**Iteration behavior**: On each iteration, the coder receives all previous verdicts as structured feedback and rewrites the code to address all issues.

---

## Algorithm Analyzer Agent

**Role**: Analyzes time and space complexity of each function, flags inefficiencies.

**Input fields used**: `code`, `language`

**Output**: `AgentOutput.complexity_analysis`, `AgentOutput.complexity_verdict`

**System prompt contract**:
```json
{
  "entries": [{"function_name": "...", "time_complexity": "O(...)", "space_complexity": "O(...)", "notes": "..."}],
  "overall_time": "O(...)",
  "overall_space": "O(...)",
  "acceptable": true,
  "confidence": 0.85,
  "issues": [{"description": "...", "suggestion": "..."}],
  "summary": "..."
}
```

**Gate classification**: Advisory (non-blocking by default). Set as blocking in config if strict complexity requirements are needed.

---

## Code Reviewer Agent

**Role**: Reviews code for correctness, edge cases, thread-safety, performance, and style.

**Input fields used**: `code`, `language`

**Output**: `AgentOutput.review_verdict: ReviewVerdict`

**System prompt contract**:
```json
{
  "status": "pass|fail",
  "confidence": 0.0-1.0,
  "blocking_issues": [{"description": "...", "line_number": null, "suggestion": "..."}],
  "style_issues": [{"description": "...", "suggestion": "..."}],
  "issues": [...],
  "summary": "..."
}
```

**Gate classification**: Blocking (must pass before proceeding to parallel phase).

---

## Security Agent

**Role**: Scans code for OWASP Top 10 (2021) vulnerabilities and common CWEs.

**Input fields used**: `code`, `language`

**Output**: `AgentOutput.security_report: SecurityReport`

**System prompt contract**:
```json
{
  "status": "pass|fail",
  "confidence": 0.0-1.0,
  "findings": [
    {
      "severity": "critical|high|medium|low|info",
      "owasp_category": "A01:2021-...",
      "description": "...",
      "location": "...",
      "recommendation": "..."
    }
  ],
  "owasp_categories_checked": [...],
  "summary": "..."
}
```

**Auto-fail rule**: Any `critical` or `high` severity finding forces `status: fail` regardless of the LLM response.

**Gate classification**: Blocking.

---

## Test Cases Agent

**Role**: Generates unit tests, functional tests, and edge case tests.

**Input fields used**: `code`, `language`, `code.filename`

**Output**: `AgentOutput.test_suite: TestSuite`, `AgentOutput.test_verdict: TestVerdict`

**System prompt contract**:
```json
{
  "test_files": [{"filename": "test_<name>.py", "content": "...", "framework": "pytest"}],
  "unit_test_count": 0,
  "functional_test_count": 0,
  "coverage_estimate": 0.0,
  "summary": "..."
}
```

**Gate classification**: Non-blocking (runs in parallel phase only).

---

## Documentation Agent

**Role**: Adds Google-style docstrings and generates a README section.

**Input fields used**: `code`, `language`, `code.filename`

**Output**: `AgentOutput.documentation: Documentation`, `AgentOutput.doc_verdict: DocumentationVerdict`

**System prompt contract**:
```json
{
  "inline_docs": "<complete file content with docstrings>",
  "readme_section": "<markdown README section>",
  "has_docstrings": true,
  "has_readme_section": true,
  "confidence": 0.0-1.0,
  "summary": "..."
}
```

**Gate classification**: Advisory by default (non-blocking).

---

## Adding a Custom Agent

1. Create `src/agent_loopa/agents/my_agent.py` subclassing `BaseAgent`
2. Implement `_default_system_prompt()` and `async run(input) -> AgentOutput`
3. Instantiate in `orchestrator.py` and add to the appropriate pipeline stage
4. Add to `configs/default_pipeline.toml` under `[agents.my_agent]`
5. Classify as blocking or advisory in `[gate]` config section
