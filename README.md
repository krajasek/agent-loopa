# agent-loopa

Multi-agent SDLC harness: automated collaborative code review and refinement pipeline.

## Quick Start

```bash
# Install
uv sync

# Generate code
uv run loopa generate --task "Implement a rate limiter using token bucket" --lang python

# Review existing code
uv run loopa review --files src/my_module.py --lang python
```

## Setup

Copy `.env.example` to `.env` and set at least one provider API key:

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY (or OPENAI_API_KEY, etc.)
```

## Documentation

- [Architecture](docs/architecture.md)
- [Agents Reference](docs/agents.md)
