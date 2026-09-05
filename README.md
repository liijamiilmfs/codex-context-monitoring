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
> MVP input is manual-only. The app reads sanitized experiment files and writes local reports. It does not collect session data from Codex Desktop or Codex CLI or connect to a remote service.

## Current state

The controlled-comparison MVP reads one experiment file and generates a Matplotlib SVG and a five-section Markdown report. It compares Desktop and CLI token averages while preserving individual readings and rounded-value uncertainty. Luna, Sol, and Astra at Medium are supported. Collection is manual.

The existing CSV/snapshot workflow is the completed **proof of concept (POC)** and remains available below. The [accepted ADR](https://linear.app/rule0softworks/document/adr-compare-controlled-desktop-and-cli-context-readings-aae4bc10842d) defines the controlled-comparison MVP; Linear owns its scope and acceptance criteria.

CI, CodeQL, Dependabot, Codecov, and Release Please workflows are configured. Release Please manages version, changelog, tag, and GitHub Release updates; the package is not published to PyPI.

## Controlled-comparison MVP

Restore the locked environment with `uv sync --locked --all-groups`, then run:

```powershell
uv run codex-context-monitoring compare experiment.txt
```

This creates `experiment.svg` and `experiment.md` beside the input. The chart
shows the Desktop and CLI averages and **Desktop average minus CLI average**
in tokens. The report includes only the short summary, original readings,
statistics, warnings, and a relative chart link. Keep both outputs together.
The summary displays as literal text; Markdown punctuation is escaped in the report.
Input filenames may use any suffix. For `.md` or `.svg` inputs (case-insensitive),
output suffixes are appended to the full name: `run.md` produces `run.md.svg` and
`run.md.md`, keeping both outputs distinct from the input.

If either output exists, the command returns an error and leaves both untouched.
There is no overwrite option. Input errors produce no reports. Read, render, and
write failures return a nonzero exit status; created paths are printed only after
both files are written. The writer reserves both names exclusively and attempts
to remove newly created files if writing fails. An operating-system failure during
cleanup can leave partial files, which the error message calls out.

### Collect the 18 readings manually

1. Make separate copies of the [Luna/Medium](examples/luna-medium.template.txt),
   [Sol/Medium](examples/sol-medium.template.txt), and
   [Astra/Medium](examples/astra-medium.template.txt) templates. Replace every
   placeholder. Keep each model in its own experiment file.
2. Use the same project in Desktop and the same project folder in CLI. Keep the
   model, Medium reasoning, and all user-controlled configuration—including
   skills, tools, and instructions—matched across surfaces and unchanged
   throughout each experiment. Record the shared setup in `conditions`.
3. For each model, start three fresh Desktop tasks and three fresh CLI sessions.
   Send exactly `Reply with exactly OK. Do not inspect files or use tools.`
   Once `OK` finishes, record `/status` immediately, before further messages or
   actions. This is six readings per model, 18 across the three files.
4. Copy only the context reading into its surface section. Do not include task
   or session identifiers, account limits, credentials, private prompts, private
   project names or paths, or unrelated status information. Matching live
   settings and following the protocol are the operator's responsibility.
5. Run `compare` for each completed file. Review the SVG and Markdown locally;
   forum posting remains manual.

The [input format](docs/controlled-experiment.md) documents all eight metadata
fields, supported number formats, and validation limits. The short `summary`
is copied into the report; the rest of the setup metadata stays in the input.

To try only invented data:

```powershell
uv run codex-context-monitoring compare examples/controlled-comparison.sample.txt
```

This creates `examples/controlled-comparison.sample.svg` and
`examples/controlled-comparison.sample.md`. A second run refuses to overwrite
them. The sample is synthetic and makes no claim about actual model behavior.
Real experiments are never collected or run in CI.

## CSV proof-of-concept workflow

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

Expected result: all unit tests pass. Integration tests are opt-in and are not part of this command or CI.

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
    to_forum_ready_markdown,
    to_snapshot_metadata,
)
from codex_context_monitoring.transformers.manual_csv import parse_manual_csv

input_path = Path("examples/manual-context-usage.sample.csv")
observations = parse_manual_csv(input_path.read_text(encoding="utf-8"))
comparison = compare_snapshots(observations, "snapshot-001", "snapshot-002")


export = ForumReadyMarkdownInput(
    comparison=comparison,
    baseline_metadata=to_snapshot_metadata(observations, "snapshot-001"),
    comparison_metadata=to_snapshot_metadata(observations, "snapshot-002"),
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

The metadata transformer rejects conflicting nonblank timestamps or context
limits within a snapshot before the export is written. Missing values stay
missing; duplicate agreed values are accepted regardless of row order.
Timestamp agreement includes the parsed date, time, and UTC offset: equal
instants expressed with different offsets are reported as conflicting values.

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
| Composition Root | `app.main` | Constructs collaborators and dispatches the CLI command. | Concrete role references for startup wiring only. |
| Controller | `compare_command.CompareCommand` | Parses CLI arguments and prints success or failure. | Injected `CompareWorkflow` Service abstraction. |
| Model | `src/codex_context_monitoring/models.py`: `ContextUsageObservation`, `SourceUsageComparison`, `SnapshotUsageComparison`; `src/codex_context_monitoring/chart_models.py`: `Bar`, `BarChart`, `RenderedChart` | Holds immutable, behavior-free usage and chart data. | No behavior-role dependencies. |
| Service | `services.snapshot_comparison`; `services.experiment_comparison`; `services.compare_workflow` | Calculates snapshot or controlled-experiment results and coordinates the comparison command. | Application Models, stateless Transformers, injected Gateway, chart Provider, and calculation function signature. |
| Transformer | `src/codex_context_monitoring/transformers/manual_csv.py:parse_manual_csv`, `ValidationIssue`, `ManualCsvValidationError`; `token_delta_chart.to_token_delta_chart`; `forum_ready_markdown.SnapshotMetadata`, `ForumReadyMarkdownInput`, `to_snapshot_metadata`, `to_forum_ready_markdown` | Validates and converts in-memory input, comparison data, chart data, and Markdown output without external I/O. | Application Models, including provider-owned chart Models; no Service, Controller, or external I/O. |
| Provider | `src/codex_context_monitoring/__init__.py:__version__`; `src/codex_context_monitoring/providers/chart_renderer.py:ChartRenderer`; `src/codex_context_monitoring/providers/matplotlib_svg_chart_renderer.py:MatplotlibSvgChartRenderer` | Exposes package metadata and isolates the Matplotlib SVG implementation behind the chart capability. | Provider-owned chart Models and the isolated Matplotlib rendering capability; no Service or Controller imports. |
| Model | `experiment_models` | Immutable metadata, readings, rounding information, statistics, and warnings in one application representation family. | No behavior-role dependencies. |
| Transformer | `transformers.experiment_text`; `transformers.experiment_report` | Parses text and maps results to chart data, Markdown, output names, and encoded content. | Application and provider-owned Models; pure operations only. |
| Gateway | `gateways.experiment_files` | Exposes operator-owned input and report export in application terms. | Injected `FileConnector` abstraction and stateless report encoding Transformer. |
| Connector | `connectors.file_connector`; `connectors.local_files` | Bounded UTF-8 reads, output checks, exclusive creation, and cleanup. | Standard-library filesystem facilities; no application decisions. |

The workflow is a Service coordinator with one explicitly injected calculation
signature, `Callable[[Experiment], ExperimentComparison]`, supplied by
`compare_experiment` at startup. This is the declared same-role composition.
`ComparisonError` is workflow-owned support; parser validation errors and private
helpers belong to their parsing Transformer. The chart family stays generic;
only the chart Transformer translates application statistics into it.

Filesystem I/O stays in the Connector. The Gateway does not own experiment state
or a managed persistence lifecycle; files remain operator-owned inputs and
exports. No database or automatic collection is introduced. Architecture
direction is checked by code review; Ruff, ty, and unit tests check implementation
quality, typing, and behavior.

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

Release notes use Release Please's `github` changelog type. GitHub generates one
entry per merged pull request, so a feature commit and its merge commit do not
produce duplicate entries. Merge commits remain supported; Conventional Commits
still determine version bumps. Regenerate notes through this configured generator
instead of editing out duplicate lines by hand. Release Please updates the root
package version in `uv.lock` in the same commit as `pyproject.toml` and the release
manifest. The lockfile entry is selected by package name, leaving dependency
versions unchanged. CI still requires a locked installation.
The selector uses `name.value` because Release Please 17.6.0 wraps TOML values
with source positions. Re-run the opt-in updater test when upgrading the action.

For `dev` to `main` promotions, use a PR title beginning with `feat:` when the
promotion includes a new feature, `fix:` for patches or maintenance, and `!`
before the colon for breaking changes. Preserve that title in the merge commit.
CI checks the title against all commits reachable from `dev` but absent from
`main`, including older commits. It runs again when the PR title is edited.
This gives Release Please a current commit with the correct change type even
when the feature commits predate the previous release. Features increase the
minor version before 1.0; for example, `0.2.0` becomes `0.3.0`. Fixes increase
the patch version. Breaking changes follow the default major-version rule.

The opt-in release automation test uses `release-please@17.6.0`, matching the
pinned action. Install it with `npm install --ignore-scripts --no-audit --no-fund
--prefix <temporary-directory> release-please@17.6.0`, set
`RELEASE_PLEASE_NODE_MODULES` to that directory's `node_modules`, and run
`uv run pytest tests/integration -m integration`. The test uses synthetic data
and makes no GitHub requests. This temporary tool is not a package dependency.
