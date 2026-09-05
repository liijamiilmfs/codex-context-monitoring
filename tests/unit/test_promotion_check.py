"""Exercise the promotion check without running Git or reading event data."""

import runpy
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
from pytest_mock import MockerFixture

SCRIPT = Path(__file__).parents[2] / ".github/scripts/check_promotion.py"


@pytest.mark.parametrize(
    ("title", "messages", "valid"),
    [
        ("chore: promote dev to main", "feat: add comparison", False),
        ("fix: promote dev to main", "feat: add comparison", False),
        ("feat: promote comparison", "feat: add comparison", True),
        ("feat(cli): promote comparison", "fix: correct output", True),
        ("fix: promote corrections", "fix: correct output", True),
        ("fix: promote maintenance", "chore: update tooling", True),
        ("feat: promote changes", "feat!: change command syntax", False),
        ("feat!: promote changes", "feat!: change command syntax", True),
        (
            "fix!: promote changes",
            "fix: change output\n\nBREAKING CHANGE: format",
            True,
        ),
        (
            "fix: promote changes",
            "fix: change output\n\nBREAKING-CHANGE: format",
            False,
        ),
        ("fix: promote comparison", "Merge pull request #1\n\nfeat: comparison", False),
        ("feat: ", "feat: comparison", False),
        ("feat: title\nother text", "feat: comparison", False),
        ("fix: correction", "fix: correction\0feat: comparison", False),
    ],
)
def test_promotion_title_reflects_unreleased_changes(
    title: str, messages: str, valid: bool
) -> None:
    check = cast(Callable[[str, str], bool], runpy.run_path(str(SCRIPT))["valid_title"])
    assert check(title, messages) is valid


@pytest.mark.parametrize("valid", [True, False])
def test_command_checks_exact_commit_range(mocker: MockerFixture, valid: bool) -> None:
    mocker.patch.dict(
        "os.environ",
        {
            "BASE_SHA": "a" * 40,
            "HEAD_SHA": "b" * 40,
            "PR_TITLE": "feat: promote" if valid else "chore: promote",
        },
        clear=True,
    )
    git = mocker.patch("subprocess.run")
    git.return_value.stdout = "feat: comparison"
    with pytest.raises(SystemExit) as result:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert result.value.code == (0 if valid else 1)
    git.assert_called_once_with(
        ["git", "log", "--format=%B%x00", f"{'a' * 40}..{'b' * 40}", "--"],
        check=True,
        capture_output=True,
        text=True,
    )


def test_command_rejects_invalid_refs_before_git(mocker: MockerFixture) -> None:
    mocker.patch.dict(
        "os.environ", {"BASE_SHA": "--all", "HEAD_SHA": "b" * 40}, clear=True
    )
    git = mocker.patch("subprocess.run")
    with pytest.raises(SystemExit) as result:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert result.value.code == 1
    git.assert_not_called()
