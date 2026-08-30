import csv
from collections import Counter
from datetime import datetime
from pathlib import Path

SAMPLE_PATH = Path(__file__).parents[2] / "examples" / "manual-context-usage.sample.csv"
EXPECTED_COLUMNS = [
    "snapshot_id",
    "surface",
    "source",
    "tokens",
    "captured_at",
    "context_limit",
    "notes",
]


def test_manual_csv_sample_satisfies_the_documented_contract() -> None:
    with SAMPLE_PATH.open(encoding="utf-8", newline="") as sample_file:
        reader = csv.DictReader(sample_file)
        rows = list(reader)

    assert reader.fieldnames == EXPECTED_COLUMNS
    assert rows

    snapshot_counts = Counter(row["snapshot_id"] for row in rows)
    assert len(snapshot_counts) >= 2
    assert all(row_count >= 2 for row_count in snapshot_counts.values())

    assert {row["surface"] for row in rows} >= {"Codex Desktop", "Codex CLI"}
    assert all(row["snapshot_id"] for row in rows)
    assert all(row["surface"] for row in rows)
    assert all(row["source"] for row in rows)
    assert all(row["tokens"].isdigit() for row in rows)
    assert all(
        not row["captured_at"] or datetime.fromisoformat(row["captured_at"])
        for row in rows
    )
    assert all(
        not row["context_limit"]
        or (row["context_limit"].isdigit() and int(row["context_limit"]) > 0)
        for row in rows
    )
    assert any(
        not row[optional_column]
        for row in rows
        for optional_column in ("captured_at", "context_limit", "notes")
    )
