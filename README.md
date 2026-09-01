# codex-context-monitoring

[![CI](https://github.com/liijamiilmfs/codex-context-monitoring/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/liijamiilmfs/codex-context-monitoring/actions/workflows/ci.yml)
[![Tests: pytest](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)](https://github.com/liijamiilmfs/codex-context-monitoring/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/liijamiilmfs/codex-context-monitoring/branch/main/graph/badge.svg)](https://codecov.io/gh/liijamiilmfs/codex-context-monitoring)
[![CodeQL](https://github.com/liijamiilmfs/codex-context-monitoring/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/liijamiilmfs/codex-context-monitoring/actions/workflows/codeql.yml)
[![GitHub Release](https://img.shields.io/github/v/release/liijamiilmfs/codex-context-monitoring?display_name=tag&sort=semver)](https://github.com/liijamiilmfs/codex-context-monitoring/releases/latest)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: Apache-2.0](https://img.shields.io/github/license/liijamiilmfs/codex-context-monitoring)](LICENSE)

A Python application for analyzing and visualizing session usage across Codex Desktop on Windows and Codex CLI.

## Current state

The repository contains the Python 3.14 project scaffold and delivery foundation. It provides an importable package, a runnable local shell, smoke tests, pure Transformers for the documented manual CSV input contract and forum-ready Markdown comparison exports, a Service that compares explicit normalized snapshots by canonical source, and a static in-memory SVG chart for per-source token deltas.

CI, CodeQL, Dependabot, Codecov, and Release Please are configured. Snapshot token totals and deltas are calculated over normalized in-memory observations. Automated session ingestion and persistence have not been implemented.

### Architecture role map

Architectural roles describe responsibilities, not folders or projects. The current MVP production code implements only these roles under R0S-ARCH-LAYERS `2.0.0-rc.2`:

| Role | Production symbol | Responsibility | Permitted dependency direction |
| -- | -- | -- | -- |
| Controller | `src/codex_context_monitoring/app.py`: `main` | Handles the local CLI entry point and returns its exit status. It contains no domain decisions, persistence, outbound integration I/O, or reusable transformation. | May depend only on Service, Transformer, Provider, Contract, and Model roles. |
| Provider | `src/codex_context_monitoring/__init__.py`: `__version__` | Exposes domain-agnostic package metadata from the current process. | May depend only on Connector, Transformer, Provider, and provider-owned Model roles. Process-local metadata access stays Provider-owned; any direct external I/O must be delegated to a Connector. |
| Provider | `src/codex_context_monitoring/providers/chart_renderer.py`: `ChartRenderer`; `providers/matplotlib_svg_chart_renderer.py`: `MatplotlibSvgChartRenderer` | Defines the application-owned chart capability and its Matplotlib implementation. The implementation accepts and returns only provider-owned models, performs no filesystem I/O, and keeps Matplotlib types inside its boundary. | May depend only on Connector, Transformer, Provider, provider-owned Model roles, and its isolated external rendering capability. |
| Model | `src/codex_context_monitoring/models.py`: `ContextUsageObservation`, `SourceUsageComparison`, `SnapshotUsageComparison` | Defines immutable, behavior-free application representations for context-usage observations and snapshot-comparison results. | Has no dependencies on behavior-bearing roles. |
| Model | `src/codex_context_monitoring/chart_models.py`: `Bar`, `BarChart`, `RenderedChart` | Defines provider-owned, domain-agnostic chart input and output representations. They are separate from context-usage domain models. | Has no dependencies on behavior-bearing roles. |
| Service | `src/codex_context_monitoring/services/snapshot_comparison.py`: `compare_snapshots` | Aggregates normalized observations for two explicit snapshots and returns canonical-source and overall token totals and deltas. It performs no parsing, external I/O, persistence, or presentation formatting. | May depend on application Models. |
| Transformer | `src/codex_context_monitoring/transformers/manual_csv.py`: `parse_manual_csv`; `transformers/token_delta_chart.py`: `to_token_delta_chart`; `transformers/forum_ready_markdown.py`: `SnapshotMetadata`, `ForumReadyMarkdownInput`, `to_forum_ready_markdown` | Purely converts complete in-memory manual CSV text into typed application Models, converts a `SnapshotUsageComparison` into a provider-owned generic `BarChart`, or formats comparison evidence as portable Markdown. These Transformers perform no external I/O. | May depend on Models and Transformer-local structural validation support. |

The production source structure mirrors that map:

```text
src/codex_context_monitoring/
|-- __init__.py  # Provider: package-version metadata
|-- app.py       # Controller: local CLI entry point
|-- chart_models.py  # Model: provider-owned generic chart data
|-- models.py    # Model: typed context-usage observations
|-- providers/
|   |-- chart_renderer.py  # Provider: narrow in-memory chart abstraction
|   `-- matplotlib_svg_chart_renderer.py  # Provider: Matplotlib SVG implementation
|-- services/
|   |-- __init__.py
|   `-- snapshot_comparison.py  # Service: snapshot totals and deltas
`-- transformers/
    |-- __init__.py
    |-- forum_ready_markdown.py  # Transformer: comparison evidence to Markdown
    |-- manual_csv.py  # Transformer: manual CSV text to Models
    `-- token_delta_chart.py  # Transformer: comparison Model to generic chart Model
```

No other architectural role is implemented yet, so the repository does not contain empty role folders or projects. New roles are added only when production responsibilities require them.

## Render the checked-in chart sample

The checked-in [token-delta SVG](examples/manual-context-usage.token-delta.svg) is generated from [the sanitized manual CSV sample](examples/manual-context-usage.sample.csv). It shows the alphabetically ordered sources, `comparison minus baseline` token deltas, both explicit snapshot IDs, and a token axis.

Regenerate it locally with:

```powershell
uv run python scripts/generate_sample_chart.py
```

The script reads `snapshot-001` as the baseline and `snapshot-002` as the comparison, then writes only the checked-in sample artifact. Production chart rendering returns in-memory SVG bytes; this sample-generation script is the intentionally separate local filesystem boundary.

## Run the local application

After installing the locked development environment, start the local shell with:

```powershell
uv run codex-context-monitoring
```

The MVP accepts session-usage data only when it is manually supplied by a later workflow. Automatic collection from Codex Desktop or Codex CLI is explicitly out of scope. The shell does not read local Codex files, connect to a remote service, or persist data.

## Development

Python 3.14 or newer and [uv](https://docs.astral.sh/uv/) are required.

```powershell
uv sync --locked --all-groups
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run coverage run -m pytest tests/unit -m "not integration"
uv run coverage report
uv run coverage xml
uv build
```

CI runs unit tests on Ubuntu and Windows. Ruff, ty, and package-build checks run on Ubuntu.

## Testing

Unit tests live under `tests/unit/`. They use pytest-mock to replace external dependencies and exercise the system under test in isolation. coverage.py measures branch coverage and enforces the configured 100% unit-test threshold. The default pytest configuration discovers unit tests only and excludes the `integration` marker.

Integration tests live under `tests/integration/`, use `@pytest.mark.integration`, and are always opt-in. When integration tests are present, run them locally with:

```powershell
uv run pytest tests/integration -m integration
```

Integration tests never run in CI.

CI uploads the unit-test `coverage.xml` report to Codecov using the user-managed `CODECOV_TOKEN` repository secret.

## Releases

[Release Please](https://github.com/googleapis/release-please) uses Conventional Commits on `main` to maintain a release pull request containing the version bump and changelog. Merging that pull request creates a `v`-prefixed Git tag and a GitHub Release.

The project is not published to PyPI.

Release Please requires a `RELEASE_PLEASE_TOKEN` repository secret so its release pull requests can trigger the required GitHub Actions workflows.
