"""Composition root for the local comparison command."""

from collections.abc import Sequence

from codex_context_monitoring.compare_command import CompareCommand
from codex_context_monitoring.connectors.local_files import LocalFileConnector
from codex_context_monitoring.gateways.experiment_files import LocalExperimentFiles
from codex_context_monitoring.providers.matplotlib_svg_chart_renderer import (
    MatplotlibSvgChartRenderer,
)
from codex_context_monitoring.services.compare_workflow import ExperimentWorkflow
from codex_context_monitoring.services.experiment_comparison import compare_experiment


def main(argv: Sequence[str] | None = None) -> int:
    """Wire concrete collaborators and dispatch the inbound command."""
    command = CompareCommand(
        ExperimentWorkflow(
            LocalExperimentFiles(LocalFileConnector()),
            MatplotlibSvgChartRenderer(),
            compare_experiment,
        )
    )
    return command.run(argv)
