"""Audit event models for the append-only audit log."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class AuditEventType(str, Enum):
    RUN_START = "run_start"
    RUN_END = "run_end"
    ITERATION_START = "iteration_start"
    ITERATION_END = "iteration_end"
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    GATE_EVALUATED = "gate_evaluated"
    PARALLEL_PHASE_START = "parallel_phase_start"
    PARALLEL_PHASE_END = "parallel_phase_end"
    ERROR = "error"


class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    event_type: AuditEventType
    timestamp: datetime = Field(default_factory=_now)
    agent_name: str | None = None
    iteration: int | None = None
    tokens_used: int = 0
    duration_ms: float | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
