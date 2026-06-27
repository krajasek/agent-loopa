# agent-loopa Architecture

## Overview

agent-loopa is a multi-agent SDLC harness that automates the collaborative review and refinement loop between senior engineers. Instead of a single LLM call, it runs a pipeline of **6 specialized agents with isolated contexts**, each iterating on each other's output until quality gates are satisfied.

## Key Design Principles

### 1. Context Isolation

Each `BaseAgent` maintains its own conversation history (`list[dict]`). No agent sees another agent's system prompt or internal reasoning. The orchestrator passes only structured `AgentInput` Pydantic objects — never raw LLM outputs or role descriptions from other agents.

### 2. Provider Agnosticism via litellm

The tool is not tied to any single LLM provider. `litellm` provides a unified async interface to 100+ providers. Configure any valid litellm model string per agent in the TOML config:

```toml
[agents.coder]
model = "gpt-4o"                          # OpenAI

[agents.algorithm_analyzer]
model = "claude-sonnet-4-6"              # Anthropic

[agents.security]
model = "gemini/gemini-1.5-pro"           # Google
```

### 3. Pipeline Stages

```
[Coder] → [AlgorithmAnalyzer] ↔ [Coder] (iterate)
        → [CodeReviewer] ↔ [Coder] (iterate)
        → [Security]       ┐
        → [TestCases]      ├── run concurrently after gate passes
        → [Documentation]  ┘
```

### 4. Iteration Loop

```python
for iteration in range(max_iterations):
    code = coder_agent.run(input + previous_verdicts)
    complexity = analyzer_agent.run(code)
    review = reviewer_agent.run(code)
    gate = QualityGate.evaluate([complexity.verdict, review.verdict])
    if gate.all_blocking_pass:
        break

# Parallel phase
security, tests, docs = await asyncio.gather(
    security_agent.run(code),
    test_agent.run(code),
    doc_agent.run(code),
)
```

### 5. Quality Gate

- **Blocking agents** (default: `security`, `code_reviewer`): ALL must emit `VerdictStatus.PASS`
- **Advisory agents** (default: `algorithm_analyzer`, `documentation`): logged but non-blocking
- **Early exit**: if all blocking agents report confidence ≥ `early_exit_confidence` (default 0.9), stop early
- **Hard cap**: `max_iterations` (default 3, configurable up to 10)

### 6. Audit Trail

Every pipeline event is appended as a JSONL line to `output_dir/audit.jsonl`:
- `run_start` / `run_end`
- `iteration_start` / `iteration_end`
- `agent_start` / `agent_end` (with token counts)
- `gate_evaluated` (with pass/fail reason)
- `parallel_phase_start` / `parallel_phase_end`

## Directory Structure

```
src/agent_loopa/
├── __init__.py               # Public API
├── version.py
├── cli/                      # Typer CLI (loopa generate / loopa review)
├── config/                   # PipelineConfig, AppSettings, TOML loader
├── models/                   # Pydantic data models (artifacts, verdicts, messages, audit)
├── agents/                   # BaseAgent + 6 specialized agents
├── orchestrator/             # Orchestrator, QualityGate, PipelineStage
├── audit/                    # Append-only JSONL AuditLogger
└── utils/                    # retry.py (exponential backoff)
```

## Message Protocol

All inter-agent communication uses typed Pydantic models:

- `AgentInput`: task description, current code, existing files, previous verdicts, iteration info
- `AgentOutput`: agent name, iteration, one populated output field (code/analysis/verdict/etc), token count
- `BaseVerdict`: `{status, confidence, issues[], summary}` — universal verdict schema
- `CodeArtifact`: versioned with `id` + `parent_id` for lineage tracking across iterations
