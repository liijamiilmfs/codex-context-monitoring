"""Transform a snapshot comparison into portable forum-ready Markdown."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from codex_context_monitoring.models import (
    ContextUsageObservation,
    SnapshotUsageComparison,
)


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


def to_snapshot_metadata(
    observations: Iterable[ContextUsageObservation], snapshot_id: str
) -> SnapshotMetadata:
    """Map one snapshot's agreed metadata, rejecting conflicting nonblank values."""
    rows = tuple(item for item in observations if item.snapshot_id == snapshot_id)
    if not rows:
        raise ValueError("snapshot has no observations")
    timestamps = {
        item.captured_at.isoformat(): item.captured_at
        for item in rows
        if item.captured_at is not None
    }
    limits = {item.context_limit for item in rows if item.context_limit is not None}
    if len(timestamps) > 1:
        raise ValueError("conflicting captured_at values in snapshot")
    if len(limits) > 1:
        raise ValueError("conflicting context_limit values in snapshot")
    return SnapshotMetadata(
        surfaces=tuple(sorted({item.surface for item in rows})),
        captured_at=next(iter(timestamps.values()), None),
        context_limit=next(iter(limits), None),
    )


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
            f"| Baseline | {_format_integer(comparison.baseline_total_tokens)} |",
            f"| Comparison | {_format_integer(comparison.comparison_total_tokens)} |",
            f"| Delta | {_format_integer(comparison.delta_total_tokens)} |",
            "",
            "## Tokens by source",
            "",
            "| Canonical source | Baseline tokens | Comparison tokens | Delta |",
            "| --- | ---: | ---: | ---: |",
        )
    )
    lines.extend(
        "| "
        f"{_table_cell(source.source)} | "
        f"{_format_integer(source.baseline_tokens)} | "
        f"{_format_integer(source.comparison_tokens)} | "
        f"{_format_integer(source.delta_tokens)} |"
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
    return ", ".join(_literal_markdown(label) for label in labels) or "Not supplied"


def _format_timestamp(captured_at: datetime | None) -> str:
    if captured_at is None:
        return "Not supplied"
    return _inline_code(captured_at.isoformat())


def _format_context_limit(context_limit: int | None) -> str:
    if context_limit is None:
        return "Not supplied"
    return f"{_format_integer(context_limit)} tokens"


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
    text = _plain_text(value)
    delimiter = "`" * (_longest_backtick_run(text) + 1)
    if (
        text
        and not text.isspace()
        and (text[0] in {" ", "`"} or text[-1] in {" ", "`"})
    ):
        text = f" {text} "
    return f"{delimiter}{text}{delimiter}"


def _longest_backtick_run(value: str) -> int:
    longest = 0
    current = 0
    for character in value:
        if character == "`":
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _plain_text(value: str) -> str:
    return value.replace("\r", " ").replace("\n", " ")


def _table_cell(value: str) -> str:
    return _literal_markdown(value)


def _literal_markdown(value: str) -> str:
    entities = {
        "!": "&#33;",
        "#": "&#35;",
        "$": "&#36;",
        "&": "&amp;",
        "(": "&#40;",
        ")": "&#41;",
        "*": "&#42;",
        "+": "&#43;",
        "-": "&#45;",
        ".": "&#46;",
        ":": "&#58;",
        "<": "&lt;",
        ">": "&gt;",
        "[": "&#91;",
        "\\": "&#92;",
        "]": "&#93;",
        "^": "&#94;",
        "_": "&#95;",
        "`": "&#96;",
        "{": "&#123;",
        "|": "&#124;",
        "}": "&#125;",
        "~": "&#126;",
    }
    return "".join(
        entities.get(character, character) for character in _plain_text(value)
    )


def _format_integer(value: int) -> str:
    return format(Decimal(value), "f")
