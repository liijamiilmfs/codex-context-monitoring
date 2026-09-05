from dataclasses import replace
from fractions import Fraction

import pytest

from codex_context_monitoring.experiment_models import TokenAmount
from codex_context_monitoring.services.experiment_comparison import compare_experiment
from codex_context_monitoring.transformers.experiment_report import (
    to_experiment_chart,
    to_experiment_markdown,
)
from codex_context_monitoring.transformers.experiment_text import parse_experiment


@pytest.mark.parametrize("offset", [100, 0, -100])
def test_separate_statistics_and_signed_difference(
    experiment_text: str, offset: int
) -> None:
    experiment = parse_experiment(experiment_text)
    desktop = tuple(
        replace(item, used=TokenAmount(value + offset, False, 1))
        for item, value in zip(experiment.desktop, [101, 102, 104], strict=True)
    )
    cli = tuple(
        replace(item, used=TokenAmount(value, False, 1))
        for item, value in zip(experiment.cli, [101, 102, 104], strict=True)
    )
    result = compare_experiment(replace(experiment, desktop=desktop, cli=cli))
    assert result.desktop.count == result.cli.count == 3
    assert result.desktop.average == Fraction(307, 3) + offset
    assert result.desktop.minimum == 101 + offset
    assert result.desktop.maximum == 104 + offset
    assert result.cli.average == Fraction(307, 3)
    assert result.cli.minimum == 101
    assert result.cli.maximum == 104
    assert result.difference == offset
    assert not result.desktop.approximate
    assert not result.difference_approximate


def test_rounded_used_counts_affect_results_but_capacities_do_not(
    experiment_text: str,
) -> None:
    experiment = parse_experiment(experiment_text)
    result = compare_experiment(experiment)
    assert result.experiment is experiment
    assert result.desktop.average == 18800
    assert result.cli.average == 10100
    assert result.difference == 8700
    assert result.desktop.approximate and result.cli.approximate
    assert result.difference_approximate
    assert result.desktop.resolution == 100
    assert result.cli.resolution == 1000
    exact = parse_experiment(
        experiment_text.replace("18.7K", "18700").replace("10K", "10000")
    )
    result = compare_experiment(exact)
    assert not result.desktop.approximate
    assert not result.cli.approximate
    assert not result.difference_approximate


@pytest.mark.parametrize(
    ("percentage", "warns"),
    [("79", False), ("80", False), ("81", False), ("78.999", True), ("81.001", True)],
)
def test_warning_strictly_above_one_point(
    experiment_text: str, percentage: str, warns: bool
) -> None:
    experiment = parse_experiment(experiment_text)
    first = replace(
        experiment.desktop[0],
        used=TokenAmount(20, False, 1),
        capacity=TokenAmount(100, False, 1),
        percentage_left=Fraction(percentage),
    )
    result = compare_experiment(
        replace(experiment, desktop=(first,) * 3, cli=(first,) * 3)
    )
    assert len(result.warnings) == (6 if warns else 0)
    if warns:
        assert result.warnings[0].surface == "Desktop"
        assert result.warnings[0].reading_number == 1
        assert result.warnings[0].line == 12
        assert result.warnings[0].displayed == Fraction(percentage)
        assert result.warnings[0].calculated == 80


def test_minimal_report_retains_all_readings_and_only_summary(
    experiment_text: str,
) -> None:
    result = compare_experiment(parse_experiment(experiment_text))
    markdown = to_experiment_markdown(result, "experiment.svg")
    assert [line for line in markdown.splitlines() if line.startswith("#")] == [
        "## Test summary",
        "## Individual readings",
        "## Summary statistics",
        "## Warnings",
        "## Chart",
    ]
    assert r"Synthetic comparison only\." in markdown
    for item in result.experiment.desktop + result.experiment.cli:
        assert item.original in markdown
    assert "**Desktop**" in markdown and "**CLI**" in markdown
    assert "| Desktop | 3 | approximate 18,800 |" in markdown
    assert "Desktop average minus CLI average: approximate 8,700 tokens" in markdown
    assert "No percentage discrepancies greater than one percentage point." in markdown
    assert "[Comparison chart](./experiment.svg)" in markdown
    for omitted in [
        "2026-09-05",
        "Synthetic OS",
        "synthetic-desktop",
        "synthetic-cli",
        "Same sanitized project",
    ]:
        assert omitted not in markdown


def test_report_warns_without_replacing_displayed_percentage(
    experiment_text: str,
) -> None:
    result = compare_experiment(parse_experiment(experiment_text.replace("93%", "80%")))
    markdown = to_experiment_markdown(result, "chart #1(α).svg")
    assert "Context: 80% left" in markdown
    assert "Desktop reading 1 (input line 12): displayed 80% left" in markdown
    assert "tokens-based" in markdown
    assert "./chart%20%231%28%CE%B1%29.svg" in markdown


def test_chart_has_two_average_bars_and_difference_label(experiment_text: str) -> None:
    result = compare_experiment(parse_experiment(experiment_text))
    chart = to_experiment_chart(result)
    assert [bar.label for bar in chart.bars] == ["Desktop", "CLI"]
    assert [bar.value for bar in chart.bars] == [18800, 10100]
    assert chart.bars[0].value_label == "approximate 18,800"
    assert (
        "Desktop average minus CLI average: approximate 8,700 tokens" == chart.subtitle
    )
    assert chart.value_axis_label == "Average tokens used"


@pytest.mark.parametrize(
    ("used", "average", "difference"),
    [
        (18701, "18,800.33", "8,700.33"),
        (18703, "18,801", "8,701"),
        (18702, "18,800.67", "8,700.67"),
    ],
)
def test_fractional_results_use_readable_decimal_labels(
    experiment_text: str,
    used: int,
    average: str,
    difference: str,
) -> None:
    experiment = parse_experiment(
        experiment_text.replace("18.7K", str(used)).replace("10K", "10000")
    )
    result = compare_experiment(experiment)
    chart = to_experiment_chart(result)
    assert chart.bars[0].value_label == average
    assert f"{difference} tokens" in chart.subtitle
    markdown = to_experiment_markdown(result, "chart.svg")
    assert f"| Desktop | 3 | {average} |" in markdown
    assert (
        "Fractional token results are rounded to two decimal places for display."
        in markdown
    )
    assert "approximate" not in markdown


@pytest.mark.parametrize(
    ("summary", "literal"),
    [
        ("## Additional results", r"\#\# Additional results"),
        ("<script>example</script>", r"\<script\>example\<\/script\>"),
        (
            "[label](https://example.invalid)",
            r"\[label\]\(https\:\/\/example\.invalid\)",
        ),
        ("``` *bold* &copy;", r"\`\`\` \*bold\* \&copy\;"),
        ("1. item | ~text~", r"1\. item \| \~text\~"),
        (r"\## heading", r"\\\#\# heading"),
    ],
)
def test_summary_is_literal_markdown(
    experiment_text: str, summary: str, literal: str
) -> None:
    experiment = parse_experiment(
        experiment_text.replace("Synthetic comparison only.", summary)
    )
    markdown = to_experiment_markdown(compare_experiment(experiment), "chart.svg")
    assert markdown.splitlines()[2] == literal
    assert len([line for line in markdown.splitlines() if line.startswith("## ")]) == 5
    assert experiment.metadata.summary == summary
