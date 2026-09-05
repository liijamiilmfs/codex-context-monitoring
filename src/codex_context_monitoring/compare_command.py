"""CLI transport: parse arguments, invoke the service, and print its outcome."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from codex_context_monitoring.services.compare_workflow import (
    CompareWorkflow,
    ComparisonError,
)


class CompareCommand:
    def __init__(self, workflow: CompareWorkflow) -> None:
        self._workflow = workflow

    def run(self, argv: Sequence[str] | None = None) -> int:
        parser = argparse.ArgumentParser(prog="codex-context-monitoring")
        subcommands = parser.add_subparsers(dest="command")
        compare = subcommands.add_parser(
            "compare", help="Compare sanitized Desktop and CLI readings"
        )
        compare.add_argument("input", type=Path, help="UTF-8 experiment text file")
        args = parser.parse_args(argv)
        if args.command is None:
            print("Codex Context Monitoring is ready.")
            print(
                "Session data must be supplied manually; automatic Codex Desktop and CLI collection is out of scope for this MVP."
            )
            return 0
        try:
            svg, markdown = self._workflow.compare(args.input)
        except ComparisonError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        print(f"Created {svg}")
        print(f"Created {markdown}")
        return 0
