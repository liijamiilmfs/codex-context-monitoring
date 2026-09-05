"""Matplotlib implementation of the in-memory SVG chart-rendering provider."""

from copy import deepcopy
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from io import BytesIO
from sys import float_info

from matplotlib import rc_context, rcParamsDefault
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from codex_context_monitoring.chart_models import BarChart, RenderedChart

_BASE_FIGURE_HEIGHT = 4.5
_FIGURE_VERTICAL_PADDING = 1.5
_HEIGHT_PER_BAR = 0.35
_MAX_SAFE_COORDINATE = float_info.max / 16
_DECIMAL_CONTEXT = Context(prec=16, rounding=ROUND_HALF_EVEN)
_RENDERER_RC_PARAMS = deepcopy(dict(rcParamsDefault))
_RENDERER_RC_PARAMS.pop("backend", None)
_RENDERER_RC_PARAMS.update(
    {
        "svg.fonttype": "none",
        "svg.hashsalt": "codex-context-monitoring",
        "text.parse_math": False,
    }
)


def _figure_height(bar_count: int) -> float:
    return max(
        _BASE_FIGURE_HEIGHT,
        _FIGURE_VERTICAL_PADDING + (_HEIGHT_PER_BAR * bar_count),
    )


def _plot_values(
    values: tuple[int | float, ...],
) -> tuple[tuple[int | float, ...], int | float | None]:
    maximum = max((abs(value) for value in values), default=0)
    if maximum <= _MAX_SAFE_COORDINATE:
        return values, None

    with localcontext(_DECIMAL_CONTEXT):
        scaled_values = tuple(
            float(Decimal(value) / Decimal(maximum)) for value in values
        )
    return scaled_values, maximum


def _format_value(value: int | float) -> str:
    if abs(value) <= _MAX_SAFE_COORDINATE:
        return f"{value:+,}"
    with localcontext(_DECIMAL_CONTEXT):
        return f"{Decimal(value):+.3E}"


def _format_scaled_tick(position: float, maximum: int | float) -> str:
    if position == 0:
        return "0"
    with localcontext(_DECIMAL_CONTEXT) as context:
        context.prec = 4
        value = Decimal(str(position)) * Decimal(maximum)
        return f"{value:.2E}"


class MatplotlibSvgChartRenderer:
    """Render generic bar charts as static SVG bytes using Matplotlib."""

    def render(self, chart: BarChart) -> RenderedChart:
        """Render the supplied generic chart into an SVG held in memory."""
        with rc_context(_RENDERER_RC_PARAMS):
            figure = Figure(
                figsize=(8, _figure_height(len(chart.bars))),
                dpi=144,
                facecolor="white",
                layout="tight",
            )
            canvas = FigureCanvasSVG(figure)
            axes = figure.subplots()
            positions = tuple(range(len(chart.bars)))
            values = tuple(bar.value for bar in chart.bars)
            plot_values, scale_maximum = _plot_values(values)
            bars = axes.barh(positions, plot_values, color="#2672a8")
            if any(bar.value_label is not None for bar in chart.bars):
                axes.margins(x=0.2)

            axes.set_yticks(positions, labels=tuple(bar.label for bar in chart.bars))
            axes.invert_yaxis()
            axes.set_xlabel(chart.value_axis_label)
            if scale_maximum is not None:
                axes.xaxis.set_major_formatter(
                    FuncFormatter(
                        lambda position, _: _format_scaled_tick(position, scale_maximum)
                    )
                )
            axes.set_title(chart.title, loc="left", fontweight="bold")
            figure.suptitle(chart.subtitle, x=0.125, ha="left", fontsize="medium")
            axes.axvline(0, color="#4d4d4d", linewidth=0.8)
            axes.grid(axis="x", color="#d9d9d9", linewidth=0.8)
            axes.set_axisbelow(True)
            axes.bar_label(
                bars,
                labels=tuple(
                    bar.value_label
                    if bar.value_label is not None
                    else _format_value(bar.value)
                    for bar in chart.bars
                ),
                padding=3,
            )

            output = BytesIO()
            canvas.print_svg(
                output,
                metadata={"Date": None, "Creator": "codex-context-monitoring"},
            )
            content = b"\n".join(
                line.rstrip(b" \t") for line in output.getvalue().split(b"\n")
            )
            content = content.replace(b"<text ", b'<text xml:space="preserve" ')
            return RenderedChart(media_type="image/svg+xml", content=content)
