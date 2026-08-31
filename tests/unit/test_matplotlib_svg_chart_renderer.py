from codex_context_monitoring.chart_models import Bar, BarChart, RenderedChart
from codex_context_monitoring.providers.chart_renderer import ChartRenderer
from codex_context_monitoring.providers.matplotlib_svg_chart_renderer import (
    MatplotlibSvgChartRenderer,
)


def test_matplotlib_svg_chart_renderer_returns_svg_bytes_for_generic_chart() -> None:
    chart = BarChart(
        title="Token delta by source",
        subtitle="snapshot-002 minus snapshot-001",
        value_axis_label="Token delta (tokens)",
        bars=(Bar(label="System instructions", value=-20),),
    )

    rendered_chart = MatplotlibSvgChartRenderer().render(chart)
    repeated_chart = MatplotlibSvgChartRenderer().render(chart)

    assert isinstance(rendered_chart, RenderedChart)
    assert isinstance(MatplotlibSvgChartRenderer(), ChartRenderer)
    assert rendered_chart.media_type == "image/svg+xml"
    assert rendered_chart.content.startswith(b'<?xml version="1.0" encoding="utf-8"')
    assert b"Token delta by source" in rendered_chart.content
    assert b"snapshot-002 minus snapshot-001" in rendered_chart.content
    assert b"Token delta (tokens)" in rendered_chart.content
    assert b"System instructions" in rendered_chart.content
    assert all(
        line == line.rstrip(b" \t") for line in rendered_chart.content.splitlines()
    )
    assert repeated_chart == rendered_chart
