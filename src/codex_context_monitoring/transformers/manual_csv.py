"""Transform manual CSV text into context-usage models."""

import csv
import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from io import StringIO
from threading import Lock
from typing import NoReturn

from codex_context_monitoring.models import ContextUsageObservation

EXPECTED_COLUMNS = (
    "snapshot_id",
    "surface",
    "source",
    "tokens",
    "captured_at",
    "context_limit",
    "notes",
)
REQUIRED_TEXT_COLUMNS = ("snapshot_id", "surface", "source")
SURFACE_LABEL_ALIASES = {
    "codex desktop": "Codex Desktop",
    "codex-desktop": "Codex Desktop",
    "codex cli": "Codex CLI",
    "codex-cli": "Codex CLI",
}
SOURCE_LABEL_ALIASES = {
    "system instructions": "System instructions",
    "system-instructions": "System instructions",
    "user conversation": "User conversation",
    "user-conversation": "User conversation",
    "tool output": "Tool output",
    "tool-output": "Tool output",
}
INTEGER_PATTERN = re.compile(r"-?[0-9]+")
VALID_QUOTED_FIELD_PATTERN = re.compile(r'(?<![^,\r\n])"(?:[^"]|"")*"(?=$|[,\r\n])')
MAX_INTEGER_DIGITS = 4_300
_CSV_FIELD_LIMIT_LOCK = Lock()


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One stable, actionable problem found at the manual CSV boundary."""

    row: int
    field: str
    code: str
    message: str

    def describe(self) -> str:
        """Render the issue with its CSV location."""
        return f"row {self.row}, field '{self.field}': {self.message}"


class ManualCsvValidationError(ValueError):
    """All validation issues that prevented an atomic CSV transformation."""

    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__("\n".join(issue.describe() for issue in self.issues))


def parse_manual_csv(csv_text: str) -> tuple[ContextUsageObservation, ...]:
    """Parse complete in-memory CSV text or raise one aggregate validation error."""
    csv_text = csv_text.removeprefix("\ufeff")
    invalid_quote_row = _find_invalid_quote_row(csv_text)
    if invalid_quote_row is not None:
        _raise_malformed_csv(invalid_quote_row)

    with _allow_in_memory_field_sizes():
        return _parse_manual_csv(csv_text)


@contextmanager
def _allow_in_memory_field_sizes() -> Iterator[None]:
    with _CSV_FIELD_LIMIT_LOCK:
        previous_limit = csv.field_size_limit()
        try:
            csv.field_size_limit(sys.maxsize)
            yield
        finally:
            csv.field_size_limit(previous_limit)


def _find_invalid_quote_row(csv_text: str) -> int | None:
    unquoted_text = VALID_QUOTED_FIELD_PATTERN.sub(
        lambda match: match.group().replace('"', " "), csv_text
    )
    quote_index = unquoted_text.find('"')
    if quote_index == -1:
        return None
    return 1 + len(re.findall(r"\r\n|\r|\n", unquoted_text[:quote_index]))


def _parse_manual_csv(csv_text: str) -> tuple[ContextUsageObservation, ...]:
    reader = csv.reader(StringIO(csv_text, newline=""), strict=True)
    try:
        header = next(reader)
    except StopIteration:
        _raise_invalid_header()
    except csv.Error:  # pragma: no cover - defensive csv implementation fallback
        _raise_malformed_csv(reader.line_num)

    if tuple(header) != EXPECTED_COLUMNS:
        missing_columns = [
            column for column in EXPECTED_COLUMNS if column not in header
        ]
        if missing_columns:
            message = f"missing required columns: {', '.join(missing_columns)}"
            code = "missing_columns"
        else:
            message = "columns must exactly match the documented order and names"
            code = "invalid_header"
        raise ManualCsvValidationError(
            [ValidationIssue(row=1, field="header", code=code, message=message)]
        )

    observations: list[ContextUsageObservation] = []
    issues: list[ValidationIssue] = []
    while True:
        row_number = reader.line_num + 1
        try:
            values = next(reader)
        except StopIteration:
            break
        except csv.Error:  # pragma: no cover - defensive csv implementation fallback
            issues.append(
                ValidationIssue(
                    row=row_number,
                    field="csv",
                    code="malformed_csv",
                    message="input is not well-formed CSV",
                )
            )
            break

        if len(values) != len(EXPECTED_COLUMNS):
            issues.append(
                ValidationIssue(
                    row=row_number,
                    field="row",
                    code="wrong_column_count",
                    message=(
                        f"expected {len(EXPECTED_COLUMNS)} columns, got {len(values)}"
                    ),
                )
            )
            continue

        observation, row_issues = _parse_row(row_number, values)
        issues.extend(row_issues)
        if observation is not None:
            observations.append(observation)

    if issues:
        raise ManualCsvValidationError(issues)
    return tuple(observations)


def _parse_row(
    row_number: int, values: list[str]
) -> tuple[ContextUsageObservation | None, list[ValidationIssue]]:
    row = dict(zip(EXPECTED_COLUMNS, values, strict=True))
    issues: list[ValidationIssue] = []

    for field in REQUIRED_TEXT_COLUMNS:
        if not row[field].strip():
            issues.append(
                ValidationIssue(
                    row=row_number,
                    field=field,
                    code="blank_required",
                    message="value must not be blank",
                )
            )

    tokens = _parse_tokens(row_number, row["tokens"], issues)
    captured_at = _parse_timestamp(row_number, row["captured_at"], issues)
    context_limit = _parse_context_limit(row_number, row["context_limit"], issues)
    if issues:
        return None, issues

    raw_surface = row["surface"]
    raw_source = row["source"]
    return (
        ContextUsageObservation(
            snapshot_id=row["snapshot_id"],
            surface=_normalize_label(raw_surface, SURFACE_LABEL_ALIASES),
            raw_surface=raw_surface,
            source=_normalize_label(raw_source, SOURCE_LABEL_ALIASES),
            raw_source=raw_source,
            tokens=tokens,
            captured_at=captured_at,
            context_limit=context_limit,
            notes=row["notes"] or None,
        ),
        issues,
    )


def _normalize_label(value: str, aliases: dict[str, str]) -> str:
    trimmed_value = value.strip()
    return aliases.get(trimmed_value.casefold(), trimmed_value)


def _parse_tokens(row_number: int, value: str, issues: list[ValidationIssue]) -> int:
    if INTEGER_PATTERN.fullmatch(value) is None:
        issues.append(
            ValidationIssue(
                row=row_number,
                field="tokens",
                code="invalid_integer",
                message="value must be a base-10 integer",
            )
        )
        return 0
    if len(value.removeprefix("-")) > MAX_INTEGER_DIGITS:
        issues.append(
            ValidationIssue(
                row=row_number,
                field="tokens",
                code="integer_too_large",
                message=f"value must contain at most {MAX_INTEGER_DIGITS} digits",
            )
        )
        return 0

    tokens = int(value)
    if tokens < 0:
        issues.append(
            ValidationIssue(
                row=row_number,
                field="tokens",
                code="negative_integer",
                message="value must be greater than or equal to zero",
            )
        )
    return tokens


def _parse_timestamp(
    row_number: int, value: str, issues: list[ValidationIssue]
) -> datetime | None:
    if not value:
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        pass
    else:
        issues.append(
            ValidationIssue(
                row=row_number,
                field="captured_at",
                code="invalid_timestamp",
                message="value must be an ISO 8601 timestamp or blank",
            )
        )
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        issues.append(
            ValidationIssue(
                row=row_number,
                field="captured_at",
                code="invalid_timestamp",
                message="value must be an ISO 8601 timestamp or blank",
            )
        )
        return None


def _parse_context_limit(
    row_number: int, value: str, issues: list[ValidationIssue]
) -> int | None:
    if not value:
        return None
    if INTEGER_PATTERN.fullmatch(value) is None:
        issues.append(
            ValidationIssue(
                row=row_number,
                field="context_limit",
                code="invalid_integer",
                message="value must be a base-10 integer or blank",
            )
        )
        return None
    if len(value.removeprefix("-")) > MAX_INTEGER_DIGITS:
        issues.append(
            ValidationIssue(
                row=row_number,
                field="context_limit",
                code="integer_too_large",
                message=f"value must contain at most {MAX_INTEGER_DIGITS} digits or be blank",
            )
        )
        return None

    context_limit = int(value)
    if context_limit <= 0:
        issues.append(
            ValidationIssue(
                row=row_number,
                field="context_limit",
                code="nonpositive_integer",
                message="value must be greater than zero or blank",
            )
        )
    return context_limit


def _raise_invalid_header() -> NoReturn:
    raise ManualCsvValidationError(
        [
            ValidationIssue(
                row=1,
                field="header",
                code="invalid_header",
                message="header is required",
            )
        ]
    )


def _raise_malformed_csv(row_number: int) -> NoReturn:
    raise ManualCsvValidationError(
        [
            ValidationIssue(
                row=max(row_number, 1),
                field="csv",
                code="malformed_csv",
                message="input is not well-formed CSV",
            )
        ]
    )
