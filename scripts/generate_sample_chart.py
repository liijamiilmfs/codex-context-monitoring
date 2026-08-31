"""Generate the checked-in chart sample from the checked-in CSV sample."""

from pathlib import Path

from codex_context_monitoring.providers.matplotlib_svg_chart_renderer import (
    MatplotlibSvgChartRenderer,
)
from codex_context_monitoring.services.snapshot_comparison import compare_snapshots
from codex_context_monitoring.transformers.manual_csv import parse_manual_csv
from codex_context_monitoring.transformers.token_delta_chart import to_token_delta_chart

EXAMPLES_DIRECTORY = Path(__file__).resolve().parents[1] / "examples"
INPUT_PATH = EXAMPLES_DIRECTORY / "manual-context-usage.sample.csv"
OUTPUT_PATH = EXAMPLES_DIRECTORY / "manual-context-usage.token-delta.svg"


def main() -> None:
    """Render the explicit sample snapshots to the checked-in SVG artifact."""
    observations = parse_manual_csv(INPUT_PATH.read_text(encoding="utf-8"))
    comparison = compare_snapshots(observations, "snapshot-001", "snapshot-002")
    chart = to_token_delta_chart(comparison)
    rendered_chart = MatplotlibSvgChartRenderer().render(chart)
    OUTPUT_PATH.write_bytes(rendered_chart.content)


if __name__ == "__main__":
    main()
