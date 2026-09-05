import pytest

from codex_context_monitoring.models import (
    ContextUsageObservation,
    SnapshotUsageComparison,
    SourceUsageComparison,
)
from codex_context_monitoring.services.snapshot_comparison import (
    UnknownSnapshotError,
    compare_snapshots,
)


def _observation(snapshot_id: str, source: str, tokens: int) -> ContextUsageObservation:
    return ContextUsageObservation(
        snapshot_id=snapshot_id,
        surface="Synthetic surface",
        raw_surface="Synthetic surface",
        source=source,
        raw_source=source,
        tokens=tokens,
        captured_at=None,
        context_limit=None,
        notes=None,
    )


def test_compare_snapshots_aggregates_sources_and_calculates_all_deltas() -> None:
    observations = (
        _observation("baseline", "System instructions", 100),
        _observation("baseline", "System instructions", 20),
        _observation("baseline", "Tool output", 50),
        _observation("baseline", "User conversation", 10),
        _observation("baseline", "Baseline only", 7),
        _observation("comparison", "System instructions", 70),
        _observation("comparison", "System instructions", 20),
        _observation("comparison", "Tool output", 80),
        _observation("comparison", "User conversation", 10),
        _observation("comparison", "Comparison only", 5),
        _observation("irrelevant", "Ignored source", 1_000),
    )

    result = compare_snapshots(observations, "baseline", "comparison")

    assert result == SnapshotUsageComparison(
        baseline_snapshot_id="baseline",
        comparison_snapshot_id="comparison",
        sources=(
            SourceUsageComparison(
                source="Baseline only",
                baseline_tokens=7,
                comparison_tokens=0,
                delta_tokens=-7,
            ),
            SourceUsageComparison(
                source="Comparison only",
                baseline_tokens=0,
                comparison_tokens=5,
                delta_tokens=5,
            ),
            SourceUsageComparison(
                source="System instructions",
                baseline_tokens=120,
                comparison_tokens=90,
                delta_tokens=-30,
            ),
            SourceUsageComparison(
                source="Tool output",
                baseline_tokens=50,
                comparison_tokens=80,
                delta_tokens=30,
            ),
            SourceUsageComparison(
                source="User conversation",
                baseline_tokens=10,
                comparison_tokens=10,
                delta_tokens=0,
            ),
        ),
        baseline_total_tokens=187,
        comparison_total_tokens=185,
        delta_total_tokens=-2,
    )


def test_compare_snapshots_supports_comparing_a_snapshot_to_itself() -> None:
    observations = (
        _observation("same", "Tool output", 4),
        _observation("same", "Tool output", 6),
    )

    result = compare_snapshots(observations, "same", "same")

    assert result.sources == (
        SourceUsageComparison(
            source="Tool output",
            baseline_tokens=10,
            comparison_tokens=10,
            delta_tokens=0,
        ),
    )
    assert result.baseline_total_tokens == 10
    assert result.comparison_total_tokens == 10
    assert result.delta_total_tokens == 0


@pytest.mark.parametrize(
    ("baseline_snapshot_id", "comparison_snapshot_id", "unknown_snapshot_ids"),
    [
        ("missing", "known", ("missing",)),
        ("known", "missing", ("missing",)),
        (
            "missing-baseline",
            "missing-comparison",
            ("missing-baseline", "missing-comparison"),
        ),
        ("missing", "missing", ("missing",)),
    ],
)
def test_compare_snapshots_rejects_unknown_snapshot_ids(
    baseline_snapshot_id: str,
    comparison_snapshot_id: str,
    unknown_snapshot_ids: tuple[str, ...],
) -> None:
    observations = (_observation("known", "Tool output", 1),)

    with pytest.raises(UnknownSnapshotError) as caught:
        compare_snapshots(observations, baseline_snapshot_id, comparison_snapshot_id)

    assert caught.value.snapshot_ids == unknown_snapshot_ids
    assert str(caught.value) == (
        "unknown snapshot ID(s): "
        + ", ".join(repr(value) for value in unknown_snapshot_ids)
    )
