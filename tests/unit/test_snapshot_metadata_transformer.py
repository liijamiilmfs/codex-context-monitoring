from dataclasses import replace
from datetime import UTC, datetime

import pytest

from codex_context_monitoring.models import ContextUsageObservation
from codex_context_monitoring.transformers.forum_ready_markdown import (
    SnapshotMetadata,
    to_snapshot_metadata,
)


def _observation() -> ContextUsageObservation:
    return ContextUsageObservation(
        snapshot_id="snapshot-001",
        surface="Codex CLI",
        raw_surface="Codex CLI",
        source="Tool output",
        raw_source="Tool output",
        tokens=1,
        captured_at=datetime(2026, 8, 30, 14, tzinfo=UTC),
        context_limit=258_000,
        notes=None,
    )


def test_metadata_preserves_agreed_values_and_ignores_blank_or_other_rows() -> None:
    observation = _observation()
    rows = (
        replace(
            observation, captured_at=None, context_limit=None, surface="Codex Desktop"
        ),
        observation,
        observation,
        replace(observation, snapshot_id="other", context_limit=1),
    )

    expected = SnapshotMetadata(
        surfaces=("Codex CLI", "Codex Desktop"),
        captured_at=observation.captured_at,
        context_limit=258_000,
    )
    assert to_snapshot_metadata(rows, "snapshot-001") == expected
    assert to_snapshot_metadata(reversed(rows), "snapshot-001") == expected


@pytest.mark.parametrize("field", ["captured_at", "context_limit"])
def test_metadata_rejects_conflicts_regardless_of_row_order(field: str) -> None:
    observation = _observation()
    changed = (
        replace(observation, captured_at=datetime(2026, 8, 30, 15, tzinfo=UTC))
        if field == "captured_at"
        else replace(observation, context_limit=100)
    )

    for rows in [(observation, changed), (changed, observation)]:
        with pytest.raises(ValueError, match=f"conflicting {field}"):
            to_snapshot_metadata(rows, "snapshot-001")


def test_metadata_preserves_missing_optional_values() -> None:
    observation = replace(_observation(), captured_at=None, context_limit=None)

    assert to_snapshot_metadata([observation], "snapshot-001") == SnapshotMetadata(
        surfaces=("Codex CLI",),
    )


def test_metadata_rejects_unknown_snapshot() -> None:
    with pytest.raises(ValueError, match="no observations"):
        to_snapshot_metadata([_observation()], "unknown")
