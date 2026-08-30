"""Local application entrypoint for the Codex usage monitoring shell."""


def main() -> int:
    """Start the local shell without collecting or persisting session data."""
    print("Codex Context Monitoring is ready.")
    print(
        "Session data must be supplied manually; automatic Codex Desktop and "
        "CLI collection is out of scope for this MVP."
    )
    return 0
