"""Keep dev-to-main promotion titles usable by Release Please."""

import os
import re
import subprocess


def valid_title(title: str, messages: str) -> bool:
    """Require the promotion to carry the largest unreleased change type."""
    match = re.fullmatch(r"(feat|fix)(?:\([^()\n]+\))?(!)?: \S[^\n]*", title)
    if match is None:
        return False
    lines = messages.replace("\0", "\n").splitlines()
    breaking = any(
        re.match(r"\w+(?:\([^()]+\))?!: ", line)
        or re.match(r"BREAKING[ -]CHANGE: ", line)
        for line in lines
    )
    feature = any(re.match(r"feat(?:ure)?(?:\([^()]+\))?!?: ", line) for line in lines)
    if breaking:
        return match[2] == "!"
    return match[2] == "!" or not feature or match[1] == "feat"


def main() -> int:
    base = os.environ.get("BASE_SHA", "")
    head = os.environ.get("HEAD_SHA", "")
    if not all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in (base, head)):
        print("Promotion check requires full base and head commit identifiers.")
        return 1
    messages = subprocess.run(
        ["git", "log", "--format=%B%x00", f"{base}..{head}", "--"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if not valid_title(os.environ.get("PR_TITLE", ""), messages):
        print(
            "Promotion title must use feat: for new features, fix: for patches, "
            "and ! for breaking changes. Use the largest unreleased change type "
            "and preserve this title in the merge commit."
        )
        return 1
    print("Promotion title carries the required release change type.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
