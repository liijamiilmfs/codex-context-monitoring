"""Parse the single supported experiment text format without external I/O."""

import re
from datetime import date
from fractions import Fraction

from codex_context_monitoring.experiment_models import (
    ContextReading,
    Experiment,
    ExperimentMetadata,
    TokenAmount,
)

MAX_DOCUMENT_CHARACTERS = 1_048_576
MAX_LINE_CHARACTERS = 131_072
MAX_READINGS = 10_000
MAX_TOKENS = 999_999_999_999_999
_FIELDS = (
    "date",
    "model",
    "reasoning",
    "operating_system",
    "desktop_version",
    "cli_version",
    "conditions",
    "summary",
)
_SECTIONS = ("[experiment]", "[desktop]", "[cli]")
_INVALID_CHARACTER = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]"
)
_COUNT = re.compile(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]{1,3})?K)")
_READING = re.compile(r"(.+)% left \((.*) used / (.+)\)")


class ExperimentValidationError(ValueError):
    """An actionable location and reason, without echoing untrusted input."""


def parse_experiment(text: str) -> Experiment:
    """Accept complete sanitized text, or reject it before returning any readings."""
    if len(text) > MAX_DOCUMENT_CHARACTERS:
        raise ExperimentValidationError("input exceeds 1048576 characters")
    metadata: dict[str, str] = {}
    groups: dict[str, list[ContextReading]] = {"[desktop]": [], "[cli]": []}
    section_index = -1
    lines = (
        text.removeprefix("\ufeff")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .split("\n")
    )
    for line_number, original in enumerate(lines, 1):
        if len(original) > MAX_LINE_CHARACTERS:
            raise ExperimentValidationError(
                f"line {line_number}: exceeds 131072 characters"
            )
        if _INVALID_CHARACTER.search(original):
            raise ExperimentValidationError(f"line {line_number}: prohibited character")
        line = original.strip()
        if not line:
            continue
        if line.startswith("["):
            if section_index == 2 or line != _SECTIONS[section_index + 1]:
                raise ExperimentValidationError(
                    f"line {line_number}: unknown, duplicate, or out-of-order section"
                )
            section_index += 1
        elif section_index == -1:
            raise ExperimentValidationError(
                f"line {line_number}: expected [experiment] section"
            )
        elif section_index == 0:
            _metadata_entry(line, line_number, metadata)
        else:
            if sum(map(len, groups.values())) >= MAX_READINGS:
                raise ExperimentValidationError("input exceeds 10000 readings")
            groups[_SECTIONS[section_index]].append(
                _reading(original, line_number, section_index)
            )
    if section_index != 2:
        raise ExperimentValidationError(
            "required sections: [experiment], [desktop], [cli]"
        )
    parsed_metadata = _metadata(metadata)
    desktop, cli = groups["[desktop]"], groups["[cli]"]
    if min(len(desktop), len(cli)) < 3:
        raise ExperimentValidationError("each surface requires at least three readings")
    if len(desktop) != len(cli):
        raise ExperimentValidationError(
            "Desktop and CLI must have equal reading counts"
        )
    if len({item.capacity.value for item in desktop + cli}) != 1:
        raise ExperimentValidationError(
            "all readings must have equal context-window capacities"
        )
    return Experiment(parsed_metadata, tuple(desktop), tuple(cli))


def _metadata_entry(line: str, number: int, metadata: dict[str, str]) -> None:
    name, separator, value = line.partition("=")
    if not separator:
        raise ExperimentValidationError(f"line {number}: expected name = value")
    name, value = name.strip(), value.strip()
    if name not in _FIELDS:
        raise ExperimentValidationError(f"line {number}: unknown metadata field")
    if name in metadata:
        raise ExperimentValidationError(f"line {number}: duplicate {name}")
    if not value:
        raise ExperimentValidationError(f"line {number}: {name} must not be blank")
    metadata[name] = value


def _metadata(values: dict[str, str]) -> ExperimentMetadata:
    missing = [field for field in _FIELDS if field not in values]
    if missing:
        raise ExperimentValidationError(f"missing metadata: {', '.join(missing)}")
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", values["date"]):
        raise ExperimentValidationError("date must use YYYY-MM-DD")
    try:
        experiment_date = date.fromisoformat(values["date"])
    except ValueError:
        raise ExperimentValidationError("date must be a valid calendar date") from None
    if values["model"] not in {"Luna", "Sol", "Astra"}:
        raise ExperimentValidationError("model must be Luna, Sol, or Astra")
    if values["reasoning"] != "Medium":
        raise ExperimentValidationError("reasoning must be Medium")
    return ExperimentMetadata(
        date=experiment_date,
        model=values["model"],
        reasoning=values["reasoning"],
        operating_system=values["operating_system"],
        desktop_version=values["desktop_version"],
        cli_version=values["cli_version"],
        conditions=values["conditions"],
        summary=values["summary"],
    )


def _reading(original: str, number: int, section: int) -> ContextReading:
    prefix = "Context: " if section == 1 else "Context window: "
    line = original.strip()
    match = _READING.fullmatch(line.removeprefix(prefix).lstrip(" "))
    if not line.startswith(prefix) or match is None:
        raise ExperimentValidationError(
            f"line {number}: expected {prefix}<percent>% left (<tokens used> used / <capacity>)"
        )
    percentage, used_text, capacity_text = match.groups()
    used = _amount(used_text, number, "tokens used")
    capacity = _amount(capacity_text, number, "capacity")
    if capacity.value == 0 or used.value > capacity.value:
        raise ExperimentValidationError(
            f"line {number}: capacity must be positive and at least tokens used"
        )
    if len(percentage) > 128 or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", percentage):
        raise ExperimentValidationError(f"line {number}: invalid percentage left")
    percentage_left = Fraction(percentage)
    if percentage_left > 100:
        raise ExperimentValidationError(
            f"line {number}: percentage left must be between 0 and 100"
        )
    return ContextReading(original, number, used, capacity, percentage_left)


def _amount(text: str, number: int, field: str) -> TokenAmount:
    if len(text) > 32 or _COUNT.fullmatch(text) is None:
        raise ExperimentValidationError(
            f"line {number}: unreadable {field}; use an integer, grouped commas, or K with up to three decimals"
        )
    rounded = text.endswith("K")
    if rounded:
        numeric = text[:-1]
        value = int(Fraction(numeric) * 1000)
        decimals = len(numeric.partition(".")[2])
        resolution = 1000 // 10**decimals
    else:
        value = int(text.replace(",", ""))
        resolution = 1
    if value > MAX_TOKENS:
        raise ExperimentValidationError(f"line {number}: {field} exceeds {MAX_TOKENS}")
    return TokenAmount(value, rounded, resolution)
