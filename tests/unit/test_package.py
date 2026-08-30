import importlib
import sys

from pytest_mock import MockerFixture


def test_package_exposes_its_version(mocker: MockerFixture) -> None:
    version_lookup = mocker.patch("importlib.metadata.version", return_value="0.1.0")
    sys.modules.pop("codex_context_monitoring", None)

    package = importlib.import_module("codex_context_monitoring")

    assert package.__version__ == "0.1.0"
    version_lookup.assert_called_once_with("codex-context-monitoring")
