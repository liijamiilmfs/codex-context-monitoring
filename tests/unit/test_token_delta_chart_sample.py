from pathlib import Path

from codex_context_monitoring.providers.matplotlib_svg_chart_renderer import (
    MatplotlibSvgChartRenderer,
)
from codex_context_monitoring.services.snapshot_comparison import compare_snapshots
from codex_context_monitoring.transformers.manual_csv import parse_manual_csv
from codex_context_monitoring.transformers.token_delta_chart import to_token_delta_chart

EXAMPLES_DIRECTORY = Path(__file__).parents[2] / "examples"
SAMPLE_CSV_PATH = EXAMPLES_DIRECTORY / "manual-context-usage.sample.csv"
SAMPLE_CHART_PATH = EXAMPLES_DIRECTORY / "manual-context-usage.token-delta.svg"


def test_checked_in_chart_sample_describes_the_documented_snapshots() -> None:
    observations = parse_manual_csv(SAMPLE_CSV_PATH.read_text(encoding="utf-8"))

    chart = to_token_delta_chart(
        compare_snapshots(observations, "snapshot-001", "snapshot-002")
    )
    artifact = SAMPLE_CHART_PATH.read_bytes()
    rendered_chart = MatplotlibSvgChartRenderer().render(chart)

    assert chart.subtitle == "snapshot-002 minus snapshot-001"
    assert chart.value_axis_label == "Token delta (tokens)"
    assert tuple(bar.label for bar in chart.bars) == (
        "System instructions",
        "Tool output",
        "User conversation",
    )
    assert tuple(bar.value for bar in chart.bars) == (780, 830, 850)
    assert artifact.startswith(b'<?xml version="1.0" encoding="utf-8"')
    assert b"snapshot-002 minus snapshot-001" in artifact
    assert b"Token delta (tokens)" in artifact
    assert b"System instructions" in artifact
    assert b"Tool output" in artifact
    assert b"User conversation" in artifact
    assert rendered_chart.content == artifact
