"""Transform snapshot-comparison models into generic chart models."""

from codex_context_monitoring.chart_models import Bar, BarChart
from codex_context_monitoring.models import SnapshotUsageComparison


def to_token_delta_chart(comparison: SnapshotUsageComparison) -> BarChart:
    """Convert a snapshot comparison into a deterministic token-delta bar chart."""
    return BarChart(
        title="Token delta by source",
        subtitle=(
            f"{comparison.comparison_snapshot_id} minus "
            f"{comparison.baseline_snapshot_id}"
        ),
        value_axis_label="Token delta (tokens)",
        bars=tuple(
            Bar(label=source.source, value=source.delta_tokens)
            for source in sorted(comparison.sources, key=lambda source: source.source)
        ),
    )
