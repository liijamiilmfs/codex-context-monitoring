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

The repository contains the Python 3.14 project scaffold and delivery foundation. Version `0.1.0` provides an importable package, a runnable local shell, and smoke tests.

CI, CodeQL, Dependabot, Codecov, and Release Please are configured. Session ingestion, metric calculation, persistence, and visualization have not been implemented yet.

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
