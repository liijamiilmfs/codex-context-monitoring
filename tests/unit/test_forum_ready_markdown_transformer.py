from datetime import UTC, datetime

from codex_context_monitoring.models import (
    SnapshotUsageComparison,
    SourceUsageComparison,
)
from codex_context_monitoring.transformers.forum_ready_markdown import (
    ForumReadyMarkdownInput,
    SnapshotMetadata,
    to_forum_ready_markdown,
)


def _comparison() -> SnapshotUsageComparison:
    return SnapshotUsageComparison(
        baseline_snapshot_id="snapshot-001",
        comparison_snapshot_id="snapshot-002",
        sources=(
            SourceUsageComparison("System instructions", 100, 140, 40),
            SourceUsageComparison("Tool output", 20, 10, -10),
        ),
        baseline_total_tokens=120,
        comparison_total_tokens=150,
        delta_total_tokens=30,
    )


def test_to_forum_ready_markdown_includes_complete_evidence() -> None:
    export = ForumReadyMarkdownInput(
        comparison=_comparison(),
        baseline_metadata=SnapshotMetadata(
            surfaces=("Codex Desktop",),
            captured_at=datetime(2026, 8, 30, 14, tzinfo=UTC),
            context_limit=114688,
        ),
        comparison_metadata=SnapshotMetadata(
            surfaces=("Codex CLI",),
            captured_at=datetime(2026, 8, 30, 15, tzinfo=UTC),
            context_limit=114688,
        ),
        chart_reference="examples/manual-context-usage.token-delta.svg",
    )

    assert to_forum_ready_markdown(export) == (
        "# Snapshot comparison evidence\n"
        "\n"
        "- Baseline snapshot ID: `snapshot-001`\n"
        "- Comparison snapshot ID: `snapshot-002`\n"
        "- Baseline surfaces: Codex Desktop\n"
        "- Comparison surfaces: Codex CLI\n"
        "- Baseline captured at: `2026-08-30T14:00:00+00:00`\n"
        "- Comparison captured at: `2026-08-30T15:00:00+00:00`\n"
        "- Baseline context-window limit: 114688 tokens\n"
        "- Comparison context-window limit: 114688 tokens\n"
        "\n"
        "## Overall token totals\n"
        "\n"
        "| Metric | Tokens |\n"
        "| --- | ---: |\n"
        "| Baseline | 120 |\n"
        "| Comparison | 150 |\n"
        "| Delta | 30 |\n"
        "\n"
        "## Tokens by source\n"
        "\n"
        "| Canonical source | Baseline tokens | Comparison tokens | Delta |\n"
        "| --- | ---: | ---: | ---: |\n"
        "| System instructions | 100 | 140 | 40 |\n"
        "| Tool output | 20 | 10 | -10 |\n"
        "\n"
        "## Chart artifact\n"
        "\n"
        "Reference/path for generated chart artifact: "
        "`examples/manual-context-usage.token-delta.svg`\n"
        "\n"
        "## Methodology\n"
        "\n"
        "Observations were manually supplied from Codex Desktop/CLI usage "
        "information and were not automatically collected.\n"
    )


def test_to_forum_ready_markdown_calls_out_missing_optional_metadata() -> None:
    export = ForumReadyMarkdownInput(
        comparison=_comparison(),
        baseline_metadata=SnapshotMetadata(surfaces=("Codex Desktop",)),
        comparison_metadata=SnapshotMetadata(surfaces=("Codex CLI",)),
        chart_reference="[generated chart path]",
    )

    markdown = to_forum_ready_markdown(export)

    assert "- Baseline captured at: Not supplied" in markdown
    assert "- Comparison captured at: Not supplied" in markdown
    assert "- Baseline context-window limit: Not supplied" in markdown
    assert "- Comparison context-window limit: Not supplied" in markdown
    assert (
        "The following optional metadata was not supplied: "
        "baseline capture timestamp; comparison capture timestamp; "
        "baseline context-window limit; comparison context-window limit."
    ) in markdown


def test_to_forum_ready_markdown_is_deterministic_for_normalized_input() -> None:
    export = ForumReadyMarkdownInput(
        comparison=_comparison(),
        baseline_metadata=SnapshotMetadata(surfaces=("Codex Desktop", "Codex Desktop")),
        comparison_metadata=SnapshotMetadata(surfaces=("Codex CLI",)),
        chart_reference="chart.svg",
    )

    assert to_forum_ready_markdown(export) == to_forum_ready_markdown(export)


def test_to_forum_ready_markdown_keeps_backticks_inside_inline_code() -> None:
    comparison = SnapshotUsageComparison(
        baseline_snapshot_id="snapshot`` [link](https://example.test)",
        comparison_snapshot_id=" `edge` ",
        sources=(),
        baseline_total_tokens=0,
        comparison_total_tokens=0,
        delta_total_tokens=0,
    )
    export = ForumReadyMarkdownInput(
        comparison=comparison,
        baseline_metadata=SnapshotMetadata(surfaces=("Codex Desktop",)),
        comparison_metadata=SnapshotMetadata(surfaces=("Codex CLI",)),
        chart_reference="`chart`.svg",
    )

    markdown = to_forum_ready_markdown(export)

    assert (
        "- Baseline snapshot ID: ```snapshot`` [link](https://example.test)```"
    ) in markdown
    assert "- Comparison snapshot ID: ``  `edge`  ``" in markdown
    assert "Reference/path for generated chart artifact: `` `chart`.svg ``" in markdown


def test_to_forum_ready_markdown_renders_imported_labels_literally() -> None:
    comparison = SnapshotUsageComparison(
        baseline_snapshot_id="snapshot-001",
        comparison_snapshot_id="snapshot-002",
        sources=(
            SourceUsageComparison(
                "Tool | [output](https://example.test) <img>", 10, 20, 10
            ),
        ),
        baseline_total_tokens=10,
        comparison_total_tokens=20,
        delta_total_tokens=10,
    )
    export = ForumReadyMarkdownInput(
        comparison=comparison,
        baseline_metadata=SnapshotMetadata(
            surfaces=(
                "[Codex CLI](https://example.test)",
                '<img src="example.test/image.png">',
            )
        ),
        comparison_metadata=SnapshotMetadata(surfaces=("Codex Desktop",)),
        chart_reference="chart.svg",
    )

    markdown = to_forum_ready_markdown(export)

    assert "&#91;Codex CLI&#93;&#40;https&#58;//example&#46;test&#41;" in markdown
    assert '&lt;img src="example&#46;test/image&#46;png"&gt;' in markdown
    assert (
        "| Tool &#124; &#91;output&#93;&#40;https&#58;//example&#46;test&#41; "
        "&lt;img&gt; | 10 | 20 | 10 |"
    ) in markdown
    assert "[Codex CLI](https://example.test)" not in markdown
    assert "<img" not in markdown


def test_to_forum_ready_markdown_supports_totals_beyond_int_text_limit() -> None:
    large_total = 10**4300
    comparison = SnapshotUsageComparison(
        baseline_snapshot_id="snapshot-001",
        comparison_snapshot_id="snapshot-002",
        sources=(SourceUsageComparison("Tool output", large_total, large_total, 0),),
        baseline_total_tokens=large_total,
        comparison_total_tokens=large_total,
        delta_total_tokens=0,
    )
    export = ForumReadyMarkdownInput(
        comparison=comparison,
        baseline_metadata=SnapshotMetadata(surfaces=("Codex Desktop",)),
        comparison_metadata=SnapshotMetadata(surfaces=("Codex CLI",)),
        chart_reference="chart.svg",
    )

    markdown = to_forum_ready_markdown(export)
    expected_total = "1" + ("0" * 4300)

    assert f"| Baseline | {expected_total} |" in markdown
    assert f"| Tool output | {expected_total} | {expected_total} | 0 |" in markdown
