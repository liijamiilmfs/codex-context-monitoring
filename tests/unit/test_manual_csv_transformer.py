from datetime import UTC, datetime
from pathlib import Path

import pytest

from codex_context_monitoring.models import ContextUsageObservation
from codex_context_monitoring.transformers.manual_csv import (
    ManualCsvValidationError,
    parse_manual_csv,
)

SAMPLE_PATH = Path(__file__).parents[2] / "examples" / "manual-context-usage.sample.csv"
HEADER = "snapshot_id,surface,source,tokens,captured_at,context_limit,notes\n"


def test_parse_manual_csv_returns_typed_models_for_checked_in_sample() -> None:
    observations = parse_manual_csv(SAMPLE_PATH.read_text(encoding="utf-8"))

    assert len(observations) == 6
    assert observations[0] == ContextUsageObservation(
        snapshot_id="snapshot-001",
        surface="Codex Desktop",
        source="System instructions",
        tokens=14320,
        captured_at=datetime(2026, 8, 30, 14, tzinfo=UTC),
        context_limit=114688,
        notes="Synthetic baseline observation",
    )
    assert observations[2].captured_at is None
    assert observations[2].context_limit is None
    assert observations[1].notes is None


def test_parse_manual_csv_preserves_raw_required_labels() -> None:
    observations = parse_manual_csv(
        HEADER + " snapshot-001 , Codex Desktop , System instructions ,0,,,\n"
    )

    assert observations[0].snapshot_id == " snapshot-001 "
    assert observations[0].surface == " Codex Desktop "
    assert observations[0].source == " System instructions "


@pytest.mark.parametrize("field", ["snapshot_id", "surface", "source"])
def test_parse_manual_csv_rejects_blank_required_text(field: str) -> None:
    values = {
        "snapshot_id": "snapshot-001",
        "surface": "Codex CLI",
        "source": "Tool output",
    }
    values[field] = "   "
    csv_text = (
        HEADER
        + f"{values['snapshot_id']},{values['surface']},{values['source']},0,,,\n"
    )

    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(csv_text)

    issue = caught.value.issues[0]
    assert (issue.row, issue.field, issue.code) == (2, field, "blank_required")
    assert str(caught.value) == f"row 2, field '{field}': value must not be blank"


@pytest.mark.parametrize(
    ("tokens", "code", "message"),
    [
        ("one", "invalid_integer", "value must be a base-10 integer"),
        ("-1", "negative_integer", "value must be greater than or equal to zero"),
    ],
)
def test_parse_manual_csv_rejects_invalid_tokens(
    tokens: str, code: str, message: str
) -> None:
    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(HEADER + f"snapshot-001,Codex CLI,Tool output,{tokens},,,\n")

    issue = caught.value.issues[0]
    assert (issue.row, issue.field, issue.code, issue.message) == (
        2,
        "tokens",
        code,
        message,
    )


@pytest.mark.parametrize("field", ["tokens", "context_limit"])
def test_parse_manual_csv_reports_oversized_integers_as_validation_issues(
    field: str,
) -> None:
    values = {
        "tokens": "9" * 5_000,
        "context_limit": "1",
    }
    if field == "context_limit":
        values = {"tokens": "1", "context_limit": "9" * 5_000}

    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(
            HEADER
            + "snapshot-001,Codex CLI,Tool output,"
            + f"{values['tokens']},,{values['context_limit']},\n"
        )

    issue = caught.value.issues[0]
    assert (issue.row, issue.field, issue.code) == (2, field, "integer_too_large")


def test_parse_manual_csv_rejects_invalid_nonblank_timestamp() -> None:
    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(HEADER + "snapshot-001,Codex CLI,Tool output,1,yesterday,,\n")

    issue = caught.value.issues[0]
    assert (issue.row, issue.field, issue.code) == (
        2,
        "captured_at",
        "invalid_timestamp",
    )


def test_parse_manual_csv_rejects_date_only_captured_at() -> None:
    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(HEADER + "snapshot-001,Codex CLI,Tool output,1,2026-08-30,,\n")

    issue = caught.value.issues[0]
    assert (issue.row, issue.field, issue.code) == (
        2,
        "captured_at",
        "invalid_timestamp",
    )


@pytest.mark.parametrize(
    ("context_limit", "code"),
    [
        ("many", "invalid_integer"),
        ("0", "nonpositive_integer"),
        ("-1", "nonpositive_integer"),
    ],
)
def test_parse_manual_csv_rejects_invalid_nonblank_context_limit(
    context_limit: str, code: str
) -> None:
    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(
            HEADER + f"snapshot-001,Codex CLI,Tool output,1,,{context_limit},\n"
        )

    issue = caught.value.issues[0]
    assert (issue.row, issue.field, issue.code) == (2, "context_limit", code)


def test_parse_manual_csv_aggregates_row_errors_without_partial_results() -> None:
    csv_text = (
        HEADER
        + ",Codex CLI,Tool output,nope,,,\n"
        + "snapshot-002,,System instructions,4,invalid,0,\n"
    )

    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(csv_text)

    assert [(issue.row, issue.field) for issue in caught.value.issues] == [
        (2, "snapshot_id"),
        (2, "tokens"),
        (3, "surface"),
        (3, "captured_at"),
        (3, "context_limit"),
    ]
    assert "\n" in str(caught.value)


def test_parse_manual_csv_reports_missing_required_columns() -> None:
    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv("snapshot_id,surface,tokens,captured_at,context_limit,notes\n")

    issue = caught.value.issues[0]
    assert (issue.row, issue.field, issue.code) == (1, "header", "missing_columns")
    assert issue.message == "missing required columns: source"


@pytest.mark.parametrize(
    "header",
    [
        "surface,snapshot_id,source,tokens,captured_at,context_limit,notes\n",
        HEADER.removesuffix("\n") + ",extra\n",
        "",
    ],
)
def test_parse_manual_csv_requires_the_exact_header(header: str) -> None:
    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(header)

    issue = caught.value.issues[0]
    assert (issue.row, issue.field, issue.code) == (1, "header", "invalid_header")


@pytest.mark.parametrize(
    "row",
    [
        "snapshot-001,Codex CLI,Tool output,1,,\n",
        "snapshot-001,Codex CLI,Tool output,1,,,,extra\n",
    ],
)
def test_parse_manual_csv_rejects_rows_with_the_wrong_column_count(row: str) -> None:
    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(HEADER + row)

    issue = caught.value.issues[0]
    assert (issue.row, issue.field, issue.code) == (2, "row", "wrong_column_count")


def test_parse_manual_csv_rejects_malformed_csv() -> None:
    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(HEADER + 'snapshot-001,"Codex CLI,Tool output,1,,,\n')

    issue = caught.value.issues[0]
    assert issue.row == 2
    assert issue.field == "csv"
    assert issue.code == "malformed_csv"


def test_parse_manual_csv_rejects_bare_quote_in_unquoted_field() -> None:
    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(HEADER + 'snapshot-001,Co"dex CLI,Tool output,1,,,\n')

    issue = caught.value.issues[0]
    assert (issue.row, issue.field, issue.code) == (2, "csv", "malformed_csv")


def test_parse_manual_csv_accepts_standard_escaped_quotes() -> None:
    observations = parse_manual_csv(
        HEADER + 'snapshot-001,Codex CLI,Tool output,1,,,"say ""hello"""\n'
    )

    assert observations[0].notes == 'say "hello"'


def test_parse_manual_csv_rejects_a_malformed_header() -> None:
    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv('"unterminated')

    issue = caught.value.issues[0]
    assert (issue.row, issue.field, issue.code) == (1, "csv", "malformed_csv")


def test_parse_manual_csv_accepts_notes_larger_than_the_csv_module_default() -> None:
    notes = "n" * 131_073

    observations = parse_manual_csv(
        HEADER + f'snapshot-001,Codex CLI,Tool output,1,,,"{notes}"\n'
    )

    assert observations[0].notes == notes


def test_parse_manual_csv_uses_multiline_record_start_for_issue_row() -> None:
    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(
            HEADER + 'snapshot-001,Codex CLI,Tool output,nope,,,"line one\nline two"\n'
        )

    issue = caught.value.issues[0]
    assert (issue.row, issue.field, issue.code) == (2, "tokens", "invalid_integer")


def test_parse_manual_csv_accepts_a_single_leading_utf8_bom() -> None:
    observations = parse_manual_csv(
        "\ufeff" + HEADER + "snapshot-001,Codex CLI,Tool output,1,,,\n"
    )

    assert observations[0].snapshot_id == "snapshot-001"
