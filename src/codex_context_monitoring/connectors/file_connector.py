"""Application-owned interface for bounded local file access."""

from pathlib import Path
from typing import Protocol


class FileConnector(Protocol):
    def read_text(self, path: Path, max_bytes: int) -> str:
        """Read bounded UTF-8 input or raise an I/O/decoding/size error."""

    def check_absent(self, paths: tuple[Path, Path]) -> None:
        """Reject any existing directory entry, including dangling links."""

    def write_pair(
        self, paths: tuple[Path, Path], contents: tuple[bytes, bytes]
    ) -> None:
        """Reserve both files exclusively before writing; clean up new files on error."""
