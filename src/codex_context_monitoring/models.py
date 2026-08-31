"""Behavior-free application models for context usage observations."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ContextUsageObservation:
    """One manually captured context-usage observation."""

    snapshot_id: str
    surface: str
    raw_surface: str
    source: str
    raw_source: str
    tokens: int
    captured_at: datetime | None
    context_limit: int | None
    notes: str | None


@dataclass(frozen=True, slots=True)
class SourceUsageComparison:
    """Token totals and delta for one canonical source across two snapshots."""

    source: str
    baseline_tokens: int
    comparison_tokens: int
    delta_tokens: int


@dataclass(frozen=True, slots=True)
class SnapshotUsageComparison:
    """Per-source and overall token comparison between two snapshots."""

    baseline_snapshot_id: str
    comparison_snapshot_id: str
    sources: tuple[SourceUsageComparison, ...]
    baseline_total_tokens: int
    comparison_total_tokens: int
    delta_total_tokens: int
