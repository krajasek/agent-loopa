"""Append-only JSONL audit logger."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from agent_loopa.models.audit import AuditEvent

logger = logging.getLogger(__name__)


class AuditLogger:
    """Writes AuditEvents as JSONL to output_dir/audit.jsonl.

    Thread-safe via asyncio lock; designed for single-process async use.
    """

    def __init__(self, run_id: str, output_dir: Path, enabled: bool = True) -> None:
        self.run_id = run_id
        self.enabled = enabled
        if enabled:
            self.log_path: Path | None = output_dir / "audit.jsonl"
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.log_path = None
        self._lock = asyncio.Lock()

    async def log(self, event: AuditEvent) -> None:
        """Append *event* to the JSONL file."""
        if not self.enabled or self.log_path is None:
            return

        line = event.model_dump_json() + "\n"
        async with self._lock:
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(line)
            except OSError as exc:
                logger.error("Failed to write audit log: %s", exc)

    def read_events(self) -> list[AuditEvent]:
        """Read all events from the log file (for inspection/testing)."""
        if not self.log_path or not self.log_path.exists():
            return []
        events = []
        with open(self.log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(AuditEvent.model_validate_json(line))
                    except Exception as exc:
                        logger.warning("Skipping malformed audit line: %s", exc)
        return events
