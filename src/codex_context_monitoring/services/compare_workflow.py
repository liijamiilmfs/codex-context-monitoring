"""Coordinate one comparison through injected calculation, file, and chart roles."""

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from codex_context_monitoring.experiment_models import Experiment, ExperimentComparison
from codex_context_monitoring.gateways.experiment_files import ExperimentFiles
from codex_context_monitoring.providers.chart_renderer import ChartRenderer
from codex_context_monitoring.transformers.experiment_report import (
    report_paths,
    to_experiment_chart,
    to_experiment_markdown,
)
from codex_context_monitoring.transformers.experiment_text import (
    ExperimentValidationError,
    parse_experiment,
)


class ComparisonError(ValueError):
    """Safe, user-facing failure from the comparison workflow."""


class CompareWorkflow(Protocol):
    def compare(self, input_path: Path) -> tuple[Path, Path]:
        """Create both reports or raise ComparisonError without claiming success."""


class ExperimentWorkflow:
    def __init__(
        self,
        files: ExperimentFiles,
        renderer: ChartRenderer,
        calculate: Callable[[Experiment], ExperimentComparison],
    ) -> None:
        self._files = files
        self._renderer = renderer
        self._calculate = calculate

    def compare(self, input_path: Path) -> tuple[Path, Path]:
        try:
            paths = report_paths(input_path)
        except ValueError:
            raise ComparisonError("Provide an input path with a filename.") from None
        try:
            self._files.check_outputs(paths)
        except FileExistsError:
            raise ComparisonError(
                "An output already exists; both outputs left untouched."
            ) from None
        except OSError:
            raise ComparisonError(
                "Cannot check output paths; verify directory access."
            ) from None
        try:
            text = self._files.read_input(input_path)
        except OSError, ValueError:
            raise ComparisonError(
                "Cannot read input; use an accessible UTF-8 file no larger than 4 MiB."
            ) from None
        try:
            experiment = parse_experiment(text)
        except ExperimentValidationError as error:
            raise ComparisonError(str(error)) from None
        result = self._calculate(experiment)
        chart = to_experiment_chart(result)
        markdown = to_experiment_markdown(result, paths[0].name)
        try:
            rendered = self._renderer.render(chart)
        except Exception:
            raise ComparisonError(
                "Cannot render chart; no reports were written."
            ) from None
        try:
            self._files.write_reports(paths, rendered.content, markdown)
        except FileExistsError:
            raise ComparisonError(
                "An output already exists; existing outputs left untouched."
            ) from None
        except OSError:
            raise ComparisonError(
                "Cannot write reports; verify directory access and space. Partial files may remain if cleanup failed."
            ) from None
        return paths
