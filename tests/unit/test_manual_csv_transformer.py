import csv
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

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
        raw_surface="Codex Desktop",
        source="System instructions",
        raw_source="System instructions",
        tokens=14320,
        captured_at=datetime(2026, 8, 30, 14, tzinfo=UTC),
        context_limit=114688,
        notes="Synthetic baseline observation",
    )
    assert observations[2].captured_at is None
    assert observations[2].context_limit is None
    assert observations[1].notes is None


def test_parse_manual_csv_normalizes_labels_and_preserves_raw_values() -> None:
    observations = parse_manual_csv(
        HEADER + " snapshot-001 , CODEX-DESKTOP , SYSTEM-INSTRUCTIONS ,0,,,\n"
    )

    assert observations[0].snapshot_id == " snapshot-001 "
    assert observations[0].surface == "Codex Desktop"
    assert observations[0].raw_surface == " CODEX-DESKTOP "
    assert observations[0].source == "System instructions"
    assert observations[0].raw_source == " SYSTEM-INSTRUCTIONS "


@pytest.mark.parametrize(
    ("raw_surface", "raw_source", "surface", "source"),
    [
        (
            "codex desktop",
            "system instructions",
            "Codex Desktop",
            "System instructions",
        ),
        ("CODEX-CLI", "TOOL-OUTPUT", "Codex CLI", "Tool output"),
        (" Codex CLI ", " USER-CONVERSATION ", "Codex CLI", "User conversation"),
    ],
)
def test_parse_manual_csv_normalizes_declared_label_aliases(
    raw_surface: str, raw_source: str, surface: str, source: str
) -> None:
    observation = parse_manual_csv(
        HEADER + f"snapshot-001,{raw_surface},{raw_source},1,,,\n"
    )[0]

    assert observation.surface == surface
    assert observation.source == source


def test_parse_manual_csv_trims_unknown_labels_without_collapsing_them() -> None:
    observations = parse_manual_csv(
        HEADER
        + "snapshot-001, Custom Surface , Custom.Source ,1,,,\n"
        + "snapshot-002,custom surface,custom-source,1,,,\n"
    )

    assert [(item.surface, item.source) for item in observations] == [
        ("Custom Surface", "Custom.Source"),
        ("custom surface", "custom-source"),
    ]
    assert [(item.raw_surface, item.raw_source) for item in observations] == [
        (" Custom Surface ", " Custom.Source "),
        ("custom surface", "custom-source"),
    ]


def test_parse_manual_csv_keeps_missing_optional_fields_absent() -> None:
    observation = parse_manual_csv(
        HEADER + "snapshot-001,Codex CLI,Tool output,1,,,\n"
    )[0]

    assert observation.captured_at is None
    assert observation.context_limit is None
    assert observation.notes is None


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


def test_parse_manual_csv_rejects_notes_larger_than_the_field_limit() -> None:
    notes = "n" * 131_073

    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(HEADER + f'snapshot-001,Codex CLI,Tool output,1,,,"{notes}"\n')

    issue = caught.value.issues[0]
    assert (issue.row, issue.field, issue.code) == (2, "csv", "field_too_large")


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


def test_parse_manual_csv_bounds_document_before_scanning(
    mocker: MockerFixture,
) -> None:
    scan = mocker.patch(
        "codex_context_monitoring.transformers.manual_csv._find_invalid_quote_row"
    )

    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv("x" * 1_048_577)

    assert caught.value.issues[0].code == "document_too_large"
    scan.assert_not_called()


def test_parse_manual_csv_accepts_exact_document_size_limit() -> None:
    prefix = "snapshot-001,Codex CLI,Tool output,1,,,"
    notes = "n" * 131_072
    document = HEADER + (prefix + notes + "\n") * 7
    remaining_notes = 1_048_576 - len(document) - len(prefix) - 1
    document += prefix + "n" * remaining_notes + "\n"

    assert parse_manual_csv(document)[0].notes == notes


def test_parse_manual_csv_bounds_the_number_of_records() -> None:
    row = "snapshot-001,Codex CLI,Tool output,1,,,\n"

    assert len(parse_manual_csv(HEADER + row * 10_000)) == 10_000
    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(HEADER + row * 10_001)

    assert caught.value.issues[0].code == "too_many_rows"


def test_parse_manual_csv_bounds_header_fields() -> None:
    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv("h" * 131_073)

    assert (caught.value.issues[0].row, caught.value.issues[0].code) == (
        1,
        "field_too_large",
    )


@pytest.mark.parametrize("limit", ["field", "rows"])
def test_parse_manual_csv_preserves_earlier_issues_at_a_limit(limit: str) -> None:
    invalid_rows = "snapshot,Codex CLI,Tool,-1,,,\nmissing,columns\n"
    valid_row = "snapshot,Codex CLI,Tool,1,,,\n"
    if limit == "field":
        later_rows = "snapshot,Codex CLI,Tool,1,,," + "n" * 131_073 + "\n"
        terminal_issue = (4, "csv", "field_too_large")
    else:
        later_rows = valid_row * 9_999
        terminal_issue = (10_002, "csv", "too_many_rows")

    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(HEADER + invalid_rows + later_rows)

    assert [(issue.row, issue.field, issue.code) for issue in caught.value.issues] == [
        (2, "tokens", "negative_integer"),
        (3, "row", "wrong_column_count"),
        terminal_issue,
    ]


def test_parse_manual_csv_translates_reader_errors_and_restores_field_limit(
    mocker: MockerFixture,
) -> None:
    previous_limit = csv.field_size_limit()
    reader = mocker.MagicMock()
    reader.__next__.side_effect = [HEADER.strip().split(","), csv.Error("invalid CSV")]
    reader.line_num = 1
    mocker.patch(
        "codex_context_monitoring.transformers.manual_csv.csv.reader",
        return_value=reader,
    )

    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(HEADER + "snapshot,Codex CLI,Tool,1,,,\n")

    assert (caught.value.issues[0].row, caught.value.issues[0].code) == (
        2,
        "malformed_csv",
    )
    assert csv.field_size_limit() == previous_limit


@pytest.mark.parametrize("field", ["snapshot_id", "surface", "source", "notes"])
@pytest.mark.parametrize(
    "character", ["\x00", "\x0b", "\x1f", "\ud800", "\ufffe", "\uffff"]
)
def test_parse_manual_csv_rejects_xml_illegal_text(field: str, character: str) -> None:
    values: dict[str, str] = dict.fromkeys(HEADER.strip().split(","), "")
    values.update(
        snapshot_id="snapshot-001", surface="Codex CLI", source="Tool", tokens="1"
    )
    values[field] = f"before{character}after"
    output = StringIO()
    csv.writer(output).writerow(values.values())

    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(HEADER + output.getvalue())

    issue = caught.value.issues[0]
    assert (issue.row, issue.field, issue.code) == (2, field, "invalid_xml_character")


def test_parse_manual_csv_preserves_xml_legal_unicode_and_whitespace() -> None:
    notes = "tab\tline\ncarriage\rreturn \u0020\ud7ff\ue000\ufffd\U00010000\U0010ffff"
    output = StringIO()
    csv.writer(output).writerow(["snapshot", "Codex CLI", "Tool", "1", "", "", notes])

    assert parse_manual_csv(HEADER + output.getvalue())[0].notes == notes


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-08-30Q14:00:00",
        "2026-08-30 14:00:00",
        "20260830T140000",
        "2026-08-30T14:00:00+00:60",
        "2026-08-30T14:00:00.1234567",
        "2026-02-30T14:00:00",
        "2026-08-30T25:00:00",
    ],
)
def test_parse_manual_csv_enforces_timestamp_grammar(timestamp: str) -> None:
    with pytest.raises(ManualCsvValidationError) as caught:
        parse_manual_csv(HEADER + f"snapshot,Codex CLI,Tool,1,{timestamp},,\n")

    assert caught.value.issues[0].code == "invalid_timestamp"


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-08-30T14:00:00",
        "2026-08-30T14:00:00Z",
        "2026-08-30T14:00:00.123456+05:30",
        "2026-08-30T14:00:00,5-04:00",
    ],
)
def test_parse_manual_csv_accepts_documented_timestamps(timestamp: str) -> None:
    output = StringIO()
    csv.writer(output).writerow(
        ["snapshot", "Codex CLI", "Tool", "1", timestamp, "", ""]
    )

    assert parse_manual_csv(HEADER + output.getvalue())[
        0
    ].captured_at == datetime.fromisoformat(timestamp)
