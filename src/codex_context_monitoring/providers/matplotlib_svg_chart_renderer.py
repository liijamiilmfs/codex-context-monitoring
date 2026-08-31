"""Matplotlib implementation of the in-memory SVG chart-rendering provider."""

from io import BytesIO

from matplotlib import rc_context
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure

from codex_context_monitoring.chart_models import BarChart, RenderedChart


class MatplotlibSvgChartRenderer:
    """Render generic bar charts as static SVG bytes using Matplotlib."""

    def render(self, chart: BarChart) -> RenderedChart:
        """Render the supplied generic chart into an SVG held in memory."""
        with rc_context({"svg.hashsalt": "codex-context-monitoring"}):
            figure = Figure(
                figsize=(8, 4.5), dpi=144, facecolor="white", layout="tight"
            )
            canvas = FigureCanvasSVG(figure)
            axes = figure.subplots()
            positions = tuple(range(len(chart.bars)))
            values = tuple(bar.value for bar in chart.bars)
            bars = axes.barh(positions, values, color="#2672a8")

            axes.set_yticks(positions, labels=tuple(bar.label for bar in chart.bars))
            axes.set_xlabel(chart.value_axis_label)
            axes.set_title(chart.title, loc="left", fontweight="bold")
            figure.suptitle(chart.subtitle, x=0.125, ha="left", fontsize="medium")
            axes.axvline(0, color="#4d4d4d", linewidth=0.8)
            axes.grid(axis="x", color="#d9d9d9", linewidth=0.8)
            axes.set_axisbelow(True)
            axes.bar_label(
                bars, labels=tuple(f"{value:+,}" for value in values), padding=3
            )

            output = BytesIO()
            canvas.print_svg(
                output,
                metadata={"Date": None, "Creator": "codex-context-monitoring"},
            )
            content = b"\n".join(
                line.rstrip(b" \t") for line in output.getvalue().split(b"\n")
            )
            return RenderedChart(media_type="image/svg+xml", content=content)
