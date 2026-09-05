from fractions import Fraction

import pytest

from codex_context_monitoring.transformers.experiment_text import (
    ExperimentValidationError,
    parse_experiment,
)


@pytest.mark.parametrize("model", ["Luna", "Sol", "Astra"])
def test_supported_experiment_preserves_evidence(
    experiment_text: str, model: str
) -> None:
    experiment = parse_experiment(experiment_text.replace("Luna", model))
    assert experiment.metadata.model == model
    assert experiment.metadata.summary == "Synthetic comparison only."
    assert experiment.metadata.date.isoformat() == "2026-09-05"
    assert len(experiment.desktop) == len(experiment.cli) == 3
    first = experiment.desktop[0]
    assert first.original == "Context: 93% left (18.7K used / 258K)"
    assert first.line == 12
    assert first.used.value == 18700
    assert first.used.rounded
    assert first.used.resolution == 100
    assert first.capacity.value == 258000
    assert first.capacity.rounded
    assert first.percentage_left == Fraction(93)
    assert experiment.desktop[1].used.value == 18800
    assert not experiment.desktop[1].used.rounded
    assert not experiment.desktop[1].capacity.rounded


def test_whitespace_bom_and_extra_readings(experiment_text: str) -> None:
    text = "\ufeff" + experiment_text.replace("\n", "\r\n")
    text = text.replace(
        "[desktop]", "[desktop]\r\n  Context: 93.25% left (18.700K used / 258K)  "
    )
    text += "Context window: 100% left (0 used / 258000)\r\n"
    result = parse_experiment(text)
    assert len(result.desktop) == len(result.cli) == 4
    assert result.desktop[0].original.startswith("  Context:")
    assert result.desktop[0].original.endswith("  ")
    assert result.desktop[0].used.resolution == 1
    assert result.desktop[0].percentage_left == Fraction(373, 4)


@pytest.mark.parametrize("padding", ["  ", " " * 14])
def test_label_alignment_preserves_original_readings(
    experiment_text: str, padding: str
) -> None:
    text = experiment_text.replace("Context: ", "Context:" + padding).replace(
        "Context window: ", "Context window:" + padding
    )
    result = parse_experiment(text)
    assert result.desktop[0].original == (
        "Context:" + padding + "93% left (18.7K used / 258K)"
    )
    assert result.cli[0].original == (
        "Context window:" + padding + "96% left (10K used / 258K)"
    )
    assert result.desktop[0].percentage_left == 93
    assert result.cli[0].percentage_left == 96
    assert result.desktop[0].used.value == 18700
    assert result.cli[0].used.value == 10000


@pytest.mark.parametrize(
    "field",
    [
        "date",
        "model",
        "reasoning",
        "operating_system",
        "desktop_version",
        "cli_version",
        "conditions",
        "summary",
    ],
)
def test_requires_each_metadata_field(experiment_text: str, field: str) -> None:
    text = "\n".join(
        line
        for line in experiment_text.splitlines()
        if not line.startswith(field + " =")
    )
    with pytest.raises(ExperimentValidationError, match=field):
        parse_experiment(text)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("summary = Synthetic comparison only.", "summary = ", "summary"),
        ("date = 2026-09-05", "date = 20260905", "date"),
        ("date = 2026-09-05", "date = 2026-02-30", "date"),
        ("Luna", "Other", "model"),
        ("Medium", "High", "reasoning"),
        ("summary =", "unknown =", "metadata"),
        ("summary =", "model =", "duplicate"),
        ("summary =", "summary :", "name = value"),
        ("[desktop]", "[unknown]", "section"),
        ("[desktop]", "[experiment]", "section"),
        ("[desktop]", "[cli]", "section"),
        ("[experiment]\n", "", "section"),
        ("Context: 93% left (18.7K used / 258K)", "Context: 93% left", "line 12"),
        ("18.7K used", "used", "line 12"),
        ("18.7K used", "unknown used", "line 12"),
        ("18.7K", "18,70", "tokens used"),
        ("18.7K", "-1", "tokens used"),
        ("18.7K", "18.7", "tokens used"),
        ("18.7K", "1e4", "tokens used"),
        ("18.7K", "18.1234K", "tokens used"),
        ("18.7K", "9999999999999999", "tokens used"),
        ("18.7K", "999999999999999K", "tokens used"),
        ("258K", "0", "capacity"),
        ("258K", "bad", "capacity"),
        ("18.7K", "259K", "capacity"),
        ("258K", "259K", "capacities"),
        ("93%", "101%", "percentage"),
        ("93%", "NaN%", "percentage"),
        ("93%", "-1%", "percentage"),
        ("93%", "9" * 129 + "%", "percentage"),
        ("Context: 93% left (18.7K used / 258K)\n", "", "at least three"),
        ("[cli]", "Context: 93% left (18.7K used / 258K)\n[cli]", "equal"),
        ("Synthetic OS", "Synthetic\x00OS", "character"),
        ("Synthetic OS", "x" * 131073, "line.*131072"),
    ],
    ids=lambda value: str(value)[:60],
)
def test_rejects_invalid_input(
    experiment_text: str, old: str, new: str, message: str
) -> None:
    with pytest.raises(ExperimentValidationError, match=message):
        parse_experiment(experiment_text.replace(old, new))


@pytest.mark.parametrize("text", ["", "[experiment]\n", "[experiment]\n[desktop]\n"])
def test_requires_all_sections(text: str) -> None:
    with pytest.raises(ExperimentValidationError, match="section"):
        parse_experiment(text)


def test_document_size_limit() -> None:
    with pytest.raises(ExperimentValidationError, match="1048576"):
        parse_experiment(" " * 1048577)


@pytest.mark.parametrize("character", ["\x0b", "\x0c"])
def test_rejects_prohibited_characters_between_lines(
    experiment_text: str, character: str
) -> None:
    with pytest.raises(ExperimentValidationError, match="character"):
        parse_experiment(character + experiment_text)


def test_reading_limit(experiment_text: str) -> None:
    text = experiment_text + "Context window: 100% left (0 used / 258K)\n" * 9995
    with pytest.raises(ExperimentValidationError, match="10000"):
        parse_experiment(text)
