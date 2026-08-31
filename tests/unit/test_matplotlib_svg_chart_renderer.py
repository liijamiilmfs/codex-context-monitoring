from xml.etree import ElementTree

from matplotlib import rc_context

from codex_context_monitoring.chart_models import Bar, BarChart, RenderedChart
from codex_context_monitoring.providers.chart_renderer import ChartRenderer
from codex_context_monitoring.providers.matplotlib_svg_chart_renderer import (
    MatplotlibSvgChartRenderer,
)

SVG_NAMESPACE = "{http://www.w3.org/2000/svg}"


def _chart_with_bars(*bars: Bar) -> BarChart:
    return BarChart(
        title="Token delta by source",
        subtitle="snapshot-002 minus snapshot-001",
        value_axis_label="Token delta (tokens)",
        bars=bars,
    )


def _text_y_position(root: ElementTree.Element, label: str) -> float:
    matching_elements = (
        element
        for element in root.iter(f"{SVG_NAMESPACE}text")
        if "".join(element.itertext()) == label
    )
    element = next(matching_elements)
    return float(element.attrib["y"])


def test_matplotlib_svg_chart_renderer_returns_svg_bytes_for_generic_chart() -> None:
    chart = _chart_with_bars(Bar(label="System instructions", value=-20))

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


def test_renderer_ignores_process_level_matplotlib_configuration() -> None:
    chart = _chart_with_bars(Bar(label="System instructions", value=-20))

    expected = MatplotlibSvgChartRenderer().render(chart)
    with rc_context({"svg.fonttype": "path", "text.usetex": True}):
        rendered_chart = MatplotlibSvgChartRenderer().render(chart)

    assert rendered_chart == expected


def test_renderer_scales_values_beyond_the_floating_point_range() -> None:
    chart = _chart_with_bars(
        Bar(label="Very large source", value=10**4299),
        Bar(label="Ordinary source", value=-20),
    )

    rendered_chart = MatplotlibSvgChartRenderer().render(chart)

    ElementTree.fromstring(rendered_chart.content)
    assert b"+1.000E+4299" in rendered_chart.content
    assert b"-20" in rendered_chart.content


def test_renderer_returns_valid_svg_for_labels_containing_double_hyphens() -> None:
    chart = _chart_with_bars(Bar(label="cache--tools", value=20))

    rendered_chart = MatplotlibSvgChartRenderer().render(chart)

    root = ElementTree.fromstring(rendered_chart.content)
    assert any(
        "".join(element.itertext()) == "cache--tools"
        for element in root.iter(f"{SVG_NAMESPACE}text")
    )


def test_renderer_displays_bars_in_model_order_from_top_to_bottom() -> None:
    chart = _chart_with_bars(
        Bar(label="Alpha", value=10),
        Bar(label="Bravo", value=20),
        Bar(label="Charlie", value=30),
    )

    rendered_chart = MatplotlibSvgChartRenderer().render(chart)

    root = ElementTree.fromstring(rendered_chart.content)
    assert _text_y_position(root, "Alpha") < _text_y_position(root, "Bravo")
    assert _text_y_position(root, "Bravo") < _text_y_position(root, "Charlie")


def test_renderer_increases_figure_height_for_many_bars() -> None:
    short_chart = _chart_with_bars(Bar(label="Source 1", value=1))
    tall_chart = _chart_with_bars(
        *(Bar(label=f"Source {number}", value=number) for number in range(30))
    )

    short_root = ElementTree.fromstring(
        MatplotlibSvgChartRenderer().render(short_chart).content
    )
    tall_root = ElementTree.fromstring(
        MatplotlibSvgChartRenderer().render(tall_chart).content
    )

    short_height = float(short_root.attrib["height"].removesuffix("pt"))
    tall_height = float(tall_root.attrib["height"].removesuffix("pt"))
    assert tall_height > short_height
