from pathlib import Path

import pytest

from codex_context_monitoring.app import main
from codex_context_monitoring.chart_models import RenderedChart
from codex_context_monitoring.connectors.local_files import LocalFileConnector
from codex_context_monitoring.providers.matplotlib_svg_chart_renderer import (
    MatplotlibSvgChartRenderer,
)


@pytest.fixture
def boundaries(mocker, experiment_text: str):
    check = mocker.patch.object(LocalFileConnector, "check_absent")
    read = mocker.patch.object(
        LocalFileConnector, "read_text", return_value=experiment_text
    )
    render = mocker.patch.object(
        MatplotlibSvgChartRenderer,
        "render",
        return_value=RenderedChart("image/svg+xml", b"synthetic svg"),
    )
    write = mocker.patch.object(LocalFileConnector, "write_pair")
    return check, read, render, write


def test_compare_command_creates_both_named_reports(boundaries, capsys) -> None:
    check, read, render, write = boundaries
    assert main(["compare", "synthetic/experiment.txt"]) == 0
    paths = (Path("synthetic/experiment.svg"), Path("synthetic/experiment.md"))
    check.assert_called_once_with(paths)
    read.assert_called_once_with(Path("synthetic/experiment.txt"), 4194304)
    assert len(render.call_args.args[0].bars) == 2
    assert write.call_args.args[0] == paths
    assert write.call_args.args[1][0] == b"synthetic svg"
    markdown = write.call_args.args[1][1].decode("utf-8")
    assert "[Comparison chart](./experiment.svg)" in markdown
    captured = capsys.readouterr()
    assert "experiment.svg" in captured.out and "experiment.md" in captured.out
    assert captured.err == ""


@pytest.mark.parametrize("existing", ["svg", "md", "both"])
def test_existing_outputs_stop_before_read_or_render(
    boundaries, capsys, existing: str
) -> None:
    check, read, render, write = boundaries
    check.side_effect = FileExistsError(existing)
    assert main(["compare", "experiment.txt"]) == 1
    read.assert_not_called()
    render.assert_not_called()
    write.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "already exists" in captured.err


def test_invalid_input_produces_no_reports(boundaries, capsys) -> None:
    _, read, render, write = boundaries
    read.return_value = "[experiment]\n"
    assert main(["compare", "experiment.txt"]) == 1
    render.assert_not_called()
    write.assert_not_called()
    assert "sections" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("boundary", "error", "message"),
    [
        (0, PermissionError("synthetic"), "check output"),
        (1, OSError("synthetic"), "read input"),
        (1, UnicodeError("synthetic"), "read input"),
        (1, ValueError("synthetic"), "read input"),
        (2, RuntimeError("synthetic"), "render chart"),
        (3, OSError("synthetic"), "write reports"),
        (3, FileExistsError("synthetic"), "already exists"),
    ],
)
def test_boundary_failures_never_claim_success(
    boundaries, capsys, boundary: int, error: Exception, message: str
) -> None:
    boundaries[boundary].side_effect = error
    assert main(["compare", "experiment.txt"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert message in captured.err
    assert "synthetic" not in captured.err


@pytest.mark.parametrize(
    "arguments", [["compare"], ["unknown"], ["compare", "one.txt", "two.txt"]]
)
def test_invalid_arguments_show_usage(arguments: list[str], capsys) -> None:
    with pytest.raises(SystemExit) as error:
        main(arguments)
    assert error.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_entrypoint_uses_process_arguments(boundaries, mocker) -> None:
    mocker.patch("sys.argv", ["codex-context-monitoring", "compare", "experiment.txt"])
    assert main() == 0


def test_path_without_filename_reports_error(boundaries, capsys) -> None:
    assert main(["compare", "."]) == 1
    assert "filename" in capsys.readouterr().err
