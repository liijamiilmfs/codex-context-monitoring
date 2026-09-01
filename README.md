# codex-context-monitoring

[![CI](https://github.com/liijamiilmfs/codex-context-monitoring/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/liijamiilmfs/codex-context-monitoring/actions/workflows/ci.yml)
[![Tests: pytest](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)](https://github.com/liijamiilmfs/codex-context-monitoring/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/liijamiilmfs/codex-context-monitoring/branch/main/graph/badge.svg)](https://codecov.io/gh/liijamiilmfs/codex-context-monitoring)
[![CodeQL](https://github.com/liijamiilmfs/codex-context-monitoring/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/liijamiilmfs/codex-context-monitoring/actions/workflows/codeql.yml)
[![GitHub Release](https://img.shields.io/github/v/release/liijamiilmfs/codex-context-monitoring?display_name=tag&sort=semver)](https://github.com/liijamiilmfs/codex-context-monitoring/releases/latest)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: Apache-2.0](https://img.shields.io/github/license/liijamiilmfs/codex-context-monitoring)](LICENSE)

A Python application for analyzing and visualizing session usage across Codex Desktop on Windows and Codex CLI.

> [!IMPORTANT]
> MVP input is manual-only. The app does not collect session data from Codex Desktop or Codex CLI, connect to a remote service, or persist data.

## Current state

The local MVP parses manual CSV into normalized observations, compares named snapshots, renders static SVG token-delta charts, and formats forum-ready Markdown. The checked-in sample workflow is reproducible; automated session ingestion, persistence, and Codex Desktop/CLI collection are not implemented.

CI, CodeQL, Dependabot, Codecov, and Release Please workflows are configured. Release Please manages version, changelog, tag, and GitHub Release updates; the package is not published to PyPI.

## Local MVP workflow

Run these commands from the repository root. Python 3.14 or newer and [uv](https://docs.astral.sh/uv/) are required.

### 1. Restore the locked environment

```powershell
uv sync --locked --all-groups
```

Expected result: the command exits with status 0 and restores the runtime, test, and development tools from `uv.lock`. The package is not installed with a separate `pip` command.

### 2. Run the local application

```powershell
uv run codex-context-monitoring
```

Expected output:

```text
Codex Context Monitoring is ready.
Session data must be supplied manually; automatic Codex Desktop and CLI collection is out of scope for this MVP.
```

The shell exits after printing its readiness message; it does not perform automatic collection.

### 3. Run the automated unit-test suite

```powershell
uv run coverage run -m pytest tests/unit -m "not integration"
```

Expected result: all unit tests pass. The current suite reports `59 passed`. Integration tests are opt-in and are not part of this command or CI.

### 4. Validate and parse the checked-in sample CSV

The command below uses the production parser against [`examples/manual-context-usage.sample.csv`](examples/manual-context-usage.sample.csv):

```powershell
@'
from pathlib import Path
from codex_context_monitoring.transformers.manual_csv import parse_manual_csv

path = Path("examples/manual-context-usage.sample.csv")
observations = parse_manual_csv(path.read_text(encoding="utf-8"))
print(
    f"Validated {path.as_posix()}: "
    f"{len(observations)} observations across "
    f"{len({observation.snapshot_id for observation in observations})} snapshots."
)
'@ | uv run python -
```

Expected output:

```text
Validated examples/manual-context-usage.sample.csv: 6 observations across 2 snapshots.
```

### 5. Compare the sample snapshots

This compares `snapshot-001` (baseline) with `snapshot-002` (comparison) from the same parsed observations:

```powershell
@'
from pathlib import Path
from codex_context_monitoring.services.snapshot_comparison import compare_snapshots
from codex_context_monitoring.transformers.manual_csv import parse_manual_csv

path = Path("examples/manual-context-usage.sample.csv")
observations = parse_manual_csv(path.read_text(encoding="utf-8"))
comparison = compare_snapshots(observations, "snapshot-001", "snapshot-002")
print(f"Compared {comparison.baseline_snapshot_id} with {comparison.comparison_snapshot_id}.")
print(
    "\n".join(
        f"{source.source}: {source.delta_tokens:+,} tokens"
        for source in comparison.sources
    )
)
print(f"Overall delta: {comparison.delta_total_tokens:+,} tokens")
'@ | uv run python -
```

Expected output:

```text
Compared snapshot-001 with snapshot-002.
System instructions: +780 tokens
Tool output: +830 tokens
User conversation: +850 tokens
Overall delta: +2,460 tokens
```

### 6. Reproduce the checked-in sample chart

```powershell
uv run python scripts/generate_sample_chart.py
```

Expected result: no console output; the command regenerates [`examples/manual-context-usage.token-delta.svg`](examples/manual-context-usage.token-delta.svg) from the sample CSV and the same `snapshot-001` versus `snapshot-002` comparison. The chart shows the source deltas above. Matplotlib 3.11.x is the static SVG renderer; see the [charting library decision](docs/mvp-07-charting-library-decision.md).

### 7. Generate the forum-ready Markdown export

This command repeats the parse and comparison, carries the sample's snapshot metadata into the export, and writes a local Markdown file beside the sample data:

```powershell
@'
from pathlib import Path

from codex_context_monitoring.services.snapshot_comparison import compare_snapshots
from codex_context_monitoring.transformers.forum_ready_markdown import (
    ForumReadyMarkdownInput,
    SnapshotMetadata,
    to_forum_ready_markdown,
)
from codex_context_monitoring.transformers.manual_csv import parse_manual_csv

input_path = Path("examples/manual-context-usage.sample.csv")
observations = parse_manual_csv(input_path.read_text(encoding="utf-8"))
comparison = compare_snapshots(observations, "snapshot-001", "snapshot-002")


def metadata_for(snapshot_id: str) -> SnapshotMetadata:
    rows = tuple(item for item in observations if item.snapshot_id == snapshot_id)
    return SnapshotMetadata(
        surfaces=tuple(item.surface for item in rows),
        captured_at=next(
            (item.captured_at for item in rows if item.captured_at is not None),
            None,
        ),
        context_limit=next(
            (item.context_limit for item in rows if item.context_limit is not None),
            None,
        ),
    )


export = ForumReadyMarkdownInput(
    comparison=comparison,
    baseline_metadata=metadata_for("snapshot-001"),
    comparison_metadata=metadata_for("snapshot-002"),
    chart_reference="examples/manual-context-usage.token-delta.svg",
)
output_path = Path("examples/manual-context-usage.forum-ready.md")
output_path.write_text(to_forum_ready_markdown(export), encoding="utf-8")
print(f"Wrote {output_path.as_posix()}.")
'@ | uv run python -
```

Expected output:

```text
Wrote examples/manual-context-usage.forum-ready.md.
```

The generated file contains the comparison evidence, including overall totals of `25750` baseline tokens, `28210` comparison tokens, and `2460` delta tokens. It is a local export and is not a checked-in fixture.

## Create a new manual CSV

Copy the sanitized sample, then edit its rows without changing the header or schema:

```powershell
Copy-Item examples/manual-context-usage.sample.csv examples/my-manual-context-usage.csv
```

Keep this header exactly as written:

```text
snapshot_id,surface,source,tokens,captured_at,context_limit,notes
```

Use one row per source within a named snapshot. `snapshot_id`, `surface`, `source`, and non-negative integer `tokens` are required. Leave `captured_at`, `context_limit`, or `notes` blank when unknown; do not invent values. The complete validation, quoting, normalization, and optional-field rules are in the [manual CSV input contract](docs/manual-csv-input.md).

## Architecture role map

The map below lists only roles represented by current production symbols. It follows the Linear project resource [Software Layer Roles and Dependency Policy, R0S-ARCH-LAYERS 2.0.0-rc.2](https://linear.app/rule0softworks/document/software-layer-roles-and-dependency-policy-ddc03ba215a5).

| Role | Production symbols | Responsibility | Permitted dependency direction |
| --- | --- | --- | --- |
| Controller | `src/codex_context_monitoring/app.py:main` | Runs the local CLI entry point and returns its exit status. | No current role imports; may depend only on Service, Transformer, Provider, Contract, or Model roles. |
| Model | `src/codex_context_monitoring/models.py`: `ContextUsageObservation`, `SourceUsageComparison`, `SnapshotUsageComparison`; `src/codex_context_monitoring/chart_models.py`: `Bar`, `BarChart`, `RenderedChart` | Holds immutable, behavior-free usage and chart data. | No behavior-role dependencies. |
| Service | `src/codex_context_monitoring/services/snapshot_comparison.py:compare_snapshots`; `UnknownSnapshotError` | Aggregates two explicit snapshots into per-source and overall totals and deltas. | Application Models only. |
| Transformer | `src/codex_context_monitoring/transformers/manual_csv.py:parse_manual_csv`, `ValidationIssue`, `ManualCsvValidationError`; `token_delta_chart.to_token_delta_chart`; `forum_ready_markdown.SnapshotMetadata`, `ForumReadyMarkdownInput`, `to_forum_ready_markdown` | Validates and converts in-memory input, comparison data, chart data, and Markdown output without external I/O. | Application Models, including provider-owned chart Models; no Service, Controller, or external I/O. |
| Provider | `src/codex_context_monitoring/__init__.py:__version__`; `src/codex_context_monitoring/providers/chart_renderer.py:ChartRenderer`; `src/codex_context_monitoring/providers/matplotlib_svg_chart_renderer.py:MatplotlibSvgChartRenderer` | Exposes package metadata and isolates the Matplotlib SVG implementation behind the chart capability. | Provider-owned chart Models and the isolated Matplotlib rendering capability; no Service or Controller imports. |

Models have no behavior-role dependencies. Services use application Models; Transformers use Models and provider-owned chart Models; the chart Provider uses its chart Models and Matplotlib. No Connector, persistence, or automatic-collection role exists in this MVP.

## Development checks

Run the complete local quality gate after changes:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run coverage run -m pytest tests/unit -m "not integration"
uv run coverage report
uv run coverage xml
uv build
uv lock --check
```

Integration tests, when present, are opt-in:

```powershell
uv run pytest tests/integration -m integration
```

## Releases

[Release Please](https://github.com/googleapis/release-please) uses Conventional Commits on `main` to maintain the release pull request, version bump, changelog, tag, and GitHub Release. The project is not published to PyPI.
