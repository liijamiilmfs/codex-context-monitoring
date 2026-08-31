from codex_context_monitoring.chart_models import Bar, BarChart
from codex_context_monitoring.models import (
    SnapshotUsageComparison,
    SourceUsageComparison,
)
from codex_context_monitoring.transformers.token_delta_chart import (
    to_token_delta_chart,
)


def test_to_token_delta_chart_maps_explicit_snapshots_and_sorts_sources() -> None:
    comparison = SnapshotUsageComparison(
        baseline_snapshot_id="snapshot-001",
        comparison_snapshot_id="snapshot-002",
        sources=(
            SourceUsageComparison("User conversation", 100, 140, 40),
            SourceUsageComparison("System instructions", 200, 180, -20),
            SourceUsageComparison("Tool output", 10, 10, 0),
        ),
        baseline_total_tokens=310,
        comparison_total_tokens=330,
        delta_total_tokens=20,
    )

    chart = to_token_delta_chart(comparison)

    assert chart == BarChart(
        title="Token delta by source",
        subtitle="snapshot-002 minus snapshot-001",
        value_axis_label="Token delta (tokens)",
        bars=(
            Bar(label="System instructions", value=-20),
            Bar(label="Tool output", value=0),
            Bar(label="User conversation", value=40),
        ),
    )
