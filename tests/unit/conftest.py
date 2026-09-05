import pytest


@pytest.fixture
def experiment_text() -> str:
    return """[experiment]
date = 2026-09-05
model = Luna
reasoning = Medium
operating_system = Synthetic OS
desktop_version = synthetic-desktop
cli_version = synthetic-cli
conditions = Same sanitized project and unchanged settings.
summary = Synthetic comparison only.

[desktop]
Context: 93% left (18.7K used / 258K)
Context: 93% left (18,800 used / 258,000)
Context: 93% left (18900 used / 258000)

[cli]
Context window: 96% left (10K used / 258K)
Context window: 96% left (10,100 used / 258,000)
Context window: 96% left (10200 used / 258000)
"""
