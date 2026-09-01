"""Transform a snapshot comparison into portable forum-ready Markdown."""

from dataclasses import dataclass
from datetime import datetime

from codex_context_monitoring.models import SnapshotUsageComparison


@dataclass(frozen=True, slots=True)
class SnapshotMetadata:
    """Snapshot-level metadata needed by the Markdown representation."""

    surfaces: tuple[str, ...]
    captured_at: datetime | None = None
    context_limit: int | None = None


@dataclass(frozen=True, slots=True)
class ForumReadyMarkdownInput:
    """Comparison data and caller-supplied metadata for one Markdown export."""

    comparison: SnapshotUsageComparison
    baseline_metadata: SnapshotMetadata
    comparison_metadata: SnapshotMetadata
    chart_reference: str


def to_forum_ready_markdown(export: ForumReadyMarkdownInput) -> str:
    """Return deterministic, paste-ready Markdown for one snapshot comparison."""
    comparison = export.comparison
    lines = [
        "# Snapshot comparison evidence",
        "",
        f"- Baseline snapshot ID: {_inline_code(comparison.baseline_snapshot_id)}",
        f"- Comparison snapshot ID: {_inline_code(comparison.comparison_snapshot_id)}",
        f"- Baseline surfaces: {_format_surfaces(export.baseline_metadata.surfaces)}",
        "- Comparison surfaces: "
        f"{_format_surfaces(export.comparison_metadata.surfaces)}",
        "- Baseline captured at: "
        f"{_format_timestamp(export.baseline_metadata.captured_at)}",
        "- Comparison captured at: "
        f"{_format_timestamp(export.comparison_metadata.captured_at)}",
        "- Baseline context-window limit: "
        f"{_format_context_limit(export.baseline_metadata.context_limit)}",
        "- Comparison context-window limit: "
        f"{_format_context_limit(export.comparison_metadata.context_limit)}",
    ]

    missing_metadata = _missing_metadata(export)
    if missing_metadata:
        lines.extend(
            (
                "",
                "## Missing optional metadata",
                "",
                "The following optional metadata was not supplied: "
                f"{'; '.join(missing_metadata)}.",
            )
        )

    lines.extend(
        (
            "",
            "## Overall token totals",
            "",
            "| Metric | Tokens |",
            "| --- | ---: |",
            f"| Baseline | {comparison.baseline_total_tokens} |",
            f"| Comparison | {comparison.comparison_total_tokens} |",
            f"| Delta | {comparison.delta_total_tokens} |",
            "",
            "## Tokens by source",
            "",
            "| Canonical source | Baseline tokens | Comparison tokens | Delta |",
            "| --- | ---: | ---: | ---: |",
        )
    )
    lines.extend(
        "| "
        f"{_table_cell(source.source)} | {source.baseline_tokens} | "
        f"{source.comparison_tokens} | {source.delta_tokens} |"
        for source in sorted(comparison.sources, key=lambda source: source.source)
    )
    lines.extend(
        (
            "",
            "## Chart artifact",
            "",
            "Reference/path for generated chart artifact: "
            f"{_inline_code(export.chart_reference)}",
            "",
            "## Methodology",
            "",
            "Observations were manually supplied from Codex Desktop/CLI usage "
            "information and were not automatically collected.",
            "",
        )
    )
    return "\n".join(lines)


def _format_surfaces(surfaces: tuple[str, ...]) -> str:
    labels = sorted(dict.fromkeys(surfaces))
    return ", ".join(_plain_text(label) for label in labels) or "Not supplied"


def _format_timestamp(captured_at: datetime | None) -> str:
    if captured_at is None:
        return "Not supplied"
    return _inline_code(captured_at.isoformat())


def _format_context_limit(context_limit: int | None) -> str:
    if context_limit is None:
        return "Not supplied"
    return f"{context_limit} tokens"


def _missing_metadata(export: ForumReadyMarkdownInput) -> list[str]:
    missing: list[str] = []
    if export.baseline_metadata.captured_at is None:
        missing.append("baseline capture timestamp")
    if export.comparison_metadata.captured_at is None:
        missing.append("comparison capture timestamp")
    if export.baseline_metadata.context_limit is None:
        missing.append("baseline context-window limit")
    if export.comparison_metadata.context_limit is None:
        missing.append("comparison context-window limit")
    return missing


def _inline_code(value: str) -> str:
    return f"`{_plain_text(value)}`"


def _plain_text(value: str) -> str:
    return value.replace("\r", " ").replace("\n", " ")


def _table_cell(value: str) -> str:
    return _plain_text(value).replace("\\", "\\\\").replace("|", "\\|")
