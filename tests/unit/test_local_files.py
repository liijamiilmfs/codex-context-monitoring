from pathlib import Path

import pytest

from codex_context_monitoring.connectors.local_files import LocalFileConnector

PATHS = (Path("experiment.svg"), Path("experiment.md"))


def test_read_utf8_is_bounded(mocker) -> None:
    opened = mocker.patch.object(Path, "open")
    stream = opened.return_value.__enter__.return_value
    stream.read.return_value = b"\xef\xbb\xbfsynthetic"
    assert LocalFileConnector().read_text(Path("experiment.txt"), 20) == "synthetic"
    opened.assert_called_once_with("rb")
    stream.read.assert_called_once_with(21)


@pytest.mark.parametrize("data", [b"x" * 21, b"\xff"])
def test_read_rejects_oversize_or_invalid_utf8(mocker, data: bytes) -> None:
    opened = mocker.patch.object(Path, "open")
    opened.return_value.__enter__.return_value.read.return_value = data
    with pytest.raises(ValueError):
        LocalFileConnector().read_text(Path("experiment.txt"), 20)


@pytest.mark.parametrize(
    "exists", [(False, False), (True, False), (False, True), (True, True)]
)
def test_checks_both_outputs_including_symlink_entries(
    mocker, exists: tuple[bool, bool]
) -> None:
    mocker.patch.object(
        Path,
        "lstat",
        side_effect=[object() if item else FileNotFoundError() for item in exists],
    )
    if any(exists):
        with pytest.raises(FileExistsError):
            LocalFileConnector().check_absent(PATHS)
    else:
        LocalFileConnector().check_absent(PATHS)


def test_output_check_preserves_access_errors(mocker) -> None:
    mocker.patch.object(Path, "lstat", side_effect=PermissionError())
    with pytest.raises(PermissionError):
        LocalFileConnector().check_absent(PATHS)


def test_write_pair_reserves_both_files_exclusively(mocker) -> None:
    first, second = mocker.MagicMock(), mocker.MagicMock()
    opened = mocker.patch.object(Path, "open", side_effect=[first, second])
    LocalFileConnector().write_pair(PATHS, (b"svg", b"markdown"))
    assert opened.call_args_list == [mocker.call("xb"), mocker.call("xb")]
    first.__enter__.return_value.write.assert_called_once_with(b"svg")
    second.__enter__.return_value.write.assert_called_once_with(b"markdown")


@pytest.mark.parametrize(
    "phase", ["first_open", "second_open", "first_write", "second_write", "close"]
)
def test_write_failure_removes_only_newly_created_files(mocker, phase: str) -> None:
    first, second = mocker.MagicMock(), mocker.MagicMock()
    handles = [first, second]
    if phase == "first_open":
        handles[0] = FileExistsError()
    elif phase == "second_open":
        handles[1] = FileExistsError()
    elif phase == "first_write":
        first.__enter__.return_value.write.side_effect = OSError()
    elif phase == "second_write":
        second.__enter__.return_value.write.side_effect = OSError()
    else:
        second.__exit__.side_effect = OSError()
    mocker.patch.object(Path, "open", side_effect=handles)
    unlink = mocker.patch.object(Path, "unlink", autospec=True)
    with pytest.raises(OSError):
        LocalFileConnector().write_pair(PATHS, (b"svg", b"markdown"))
    expected = [] if phase == "first_open" else [mocker.call(PATHS[0])]
    if phase not in {"first_open", "second_open"}:
        expected.append(mocker.call(PATHS[1]))
    assert unlink.call_args_list == expected
    if phase in {"first_open", "second_open"}:
        first.__enter__.return_value.write.assert_not_called()


def test_cleanup_failure_is_reported_and_other_cleanup_is_attempted(mocker) -> None:
    opened = mocker.patch.object(Path, "open")
    opened.return_value.__enter__.return_value.write.side_effect = OSError()
    unlink = mocker.patch.object(Path, "unlink", side_effect=[PermissionError(), None])
    with pytest.raises(OSError, match="cleanup"):
        LocalFileConnector().write_pair(PATHS, (b"svg", b"markdown"))
    assert unlink.call_count == 2
