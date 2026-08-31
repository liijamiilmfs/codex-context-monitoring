"""Compare normalized context-usage observations across two snapshots."""

from collections.abc import Iterable

from codex_context_monitoring.models import (
    ContextUsageObservation,
    SnapshotUsageComparison,
    SourceUsageComparison,
)


class UnknownSnapshotError(ValueError):
    """One or more requested snapshot IDs are absent from the observations."""

    def __init__(self, snapshot_ids: tuple[str, ...]) -> None:
        self.snapshot_ids = snapshot_ids
        identifiers = ", ".join(repr(snapshot_id) for snapshot_id in snapshot_ids)
        super().__init__(f"unknown snapshot ID(s): {identifiers}")


def compare_snapshots(
    observations: Iterable[ContextUsageObservation],
    baseline_snapshot_id: str,
    comparison_snapshot_id: str,
) -> SnapshotUsageComparison:
    """Return source and overall token deltas for two explicit snapshots."""
    available_snapshot_ids: set[str] = set()
    baseline_totals: dict[str, int] = {}
    comparison_totals: dict[str, int] = {}

    for observation in observations:
        available_snapshot_ids.add(observation.snapshot_id)
        if observation.snapshot_id == baseline_snapshot_id:
            _add_tokens(baseline_totals, observation.source, observation.tokens)
        if observation.snapshot_id == comparison_snapshot_id:
            _add_tokens(comparison_totals, observation.source, observation.tokens)

    missing_snapshot_ids = tuple(
        dict.fromkeys(
            snapshot_id
            for snapshot_id in (baseline_snapshot_id, comparison_snapshot_id)
            if snapshot_id not in available_snapshot_ids
        )
    )
    if missing_snapshot_ids:
        raise UnknownSnapshotError(missing_snapshot_ids)

    sources = tuple(
        SourceUsageComparison(
            source=source,
            baseline_tokens=baseline_totals.get(source, 0),
            comparison_tokens=comparison_totals.get(source, 0),
            delta_tokens=(
                comparison_totals.get(source, 0) - baseline_totals.get(source, 0)
            ),
        )
        for source in sorted(baseline_totals.keys() | comparison_totals.keys())
    )
    baseline_total_tokens = sum(baseline_totals.values())
    comparison_total_tokens = sum(comparison_totals.values())

    return SnapshotUsageComparison(
        baseline_snapshot_id=baseline_snapshot_id,
        comparison_snapshot_id=comparison_snapshot_id,
        sources=sources,
        baseline_total_tokens=baseline_total_tokens,
        comparison_total_tokens=comparison_total_tokens,
        delta_total_tokens=comparison_total_tokens - baseline_total_tokens,
    )


def _add_tokens(totals: dict[str, int], source: str, tokens: int) -> None:
    totals[source] = totals.get(source, 0) + tokens
