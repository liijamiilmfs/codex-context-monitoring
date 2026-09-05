"""Expose experiment input and report export through an injected file connector."""

from pathlib import Path
from typing import Protocol

from codex_context_monitoring.connectors.file_connector import FileConnector
from codex_context_monitoring.transformers.experiment_report import encode_reports


class ExperimentFiles(Protocol):
    def check_outputs(self, paths: tuple[Path, Path]) -> None:
        """Raise if either target exists or cannot be checked."""

    def read_input(self, path: Path) -> str:
        """Return bounded UTF-8 input."""

    def write_reports(
        self, paths: tuple[Path, Path], svg: bytes, markdown: str
    ) -> None:
        """Create the report pair without replacing existing files."""


class LocalExperimentFiles:
    def __init__(self, connector: FileConnector) -> None:
        self._connector = connector

    def check_outputs(self, paths: tuple[Path, Path]) -> None:
        self._connector.check_absent(paths)

    def read_input(self, path: Path) -> str:
        return self._connector.read_text(path, 4_194_304)

    def write_reports(
        self, paths: tuple[Path, Path], svg: bytes, markdown: str
    ) -> None:
        self._connector.write_pair(paths, encode_reports(svg, markdown))
