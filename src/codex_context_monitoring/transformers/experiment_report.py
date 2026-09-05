"""Map a comparison into chart data and the five-section evidence report."""

from fractions import Fraction
from pathlib import Path
from urllib.parse import quote

from codex_context_monitoring.chart_models import Bar, BarChart
from codex_context_monitoring.experiment_models import ExperimentComparison


def report_paths(input_path: Path) -> tuple[Path, Path]:
    """Derive sibling output names without accessing the filesystem."""
    return input_path.with_suffix(".svg"), input_path.with_suffix(".md")


def encode_reports(svg: bytes, markdown: str) -> tuple[bytes, bytes]:
    """Map rendered content to file bytes without I/O."""
    return svg, markdown.encode("utf-8")


def _number(value: int | Fraction, approximate: bool = False) -> str:
    if approximate:
        return f"approximate {round(value):,}"
    value = Fraction(value)
    if value.denominator == 1:
        return f"{value.numerator:,}"
    return f"{value.numerator:,}/{value.denominator:,}"


def _difference(result: ExperimentComparison) -> str:
    return (
        "Desktop average minus CLI average: "
        + _number(result.difference, result.difference_approximate)
        + " tokens"
    )


def to_experiment_chart(result: ExperimentComparison) -> BarChart:
    """Two average bars; numeric labels retain exact or approximate meaning."""
    return BarChart(
        title="Desktop and CLI context usage",
        subtitle=_difference(result),
        value_axis_label="Average tokens used",
        bars=tuple(
            Bar(
                label=name,
                value=float(stats.average),
                value_label=_number(stats.average, stats.approximate),
            )
            for name, stats in (("Desktop", result.desktop), ("CLI", result.cli))
        ),
    )


def to_experiment_markdown(result: ExperimentComparison, chart_filename: str) -> str:
    """Copy the short summary and original readings; exclude other setup metadata."""
    lines = [
        "## Test summary",
        "",
        result.experiment.metadata.summary,
        "",
        "## Individual readings",
        "",
    ]
    for name, readings in (
        ("Desktop", result.experiment.desktop),
        ("CLI", result.experiment.cli),
    ):
        lines.extend((f"**{name}**", "", "```text"))
        lines.extend(item.original for item in readings)
        lines.extend(("```", ""))
    lines.extend(
        (
            "K notation in the original readings is rounded, including capacities.",
            "",
            "## Summary statistics",
            "",
            "| Surface | Count | Average tokens | Minimum tokens | Maximum tokens |",
            "| --- | ---: | ---: | ---: | ---: |",
        )
    )
    for name, stats in (("Desktop", result.desktop), ("CLI", result.cli)):
        lines.append(
            f"| {name} | {stats.count} | {_number(stats.average, stats.approximate)} | {_number(stats.minimum, stats.approximate)} | {_number(stats.maximum, stats.approximate)} |"
        )
    lines.extend(("", _difference(result), ""))
    if result.difference_approximate:
        lines.extend(
            (
                "Approximate results use rounded tokens-used input and are shown to whole tokens; calculation does not add measurement precision.",
                "",
            )
        )
    lines.extend(("## Warnings", ""))
    if result.warnings:
        for warning in result.warnings:
            lines.append(
                f"- {warning.surface} reading {warning.reading_number} (input line {warning.line}): displayed {_number(warning.displayed)}% left; tokens-based {float(warning.calculated):.2f}% left (using normalized counts). Difference exceeds one percentage point."
            )
    else:
        lines.append("No percentage discrepancies greater than one percentage point.")
    lines.extend(
        (
            "",
            "## Chart",
            "",
            f"[Comparison chart](./{quote(chart_filename, safe='')})",
            "",
        )
    )
    return "\n".join(lines)
