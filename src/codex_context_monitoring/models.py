"""Behavior-free application models for context usage observations."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ContextUsageObservation:
    """One manually captured context-usage observation."""

    snapshot_id: str
    surface: str
    source: str
    tokens: int
    captured_at: datetime | None
    context_limit: int | None
    notes: str | None
