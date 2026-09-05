"""Filesystem I/O only; no experiment parsing, calculations, or rendering."""

from contextlib import ExitStack
from pathlib import Path


class LocalFileConnector:
    def read_text(self, path: Path, max_bytes: int) -> str:
        with path.open("rb") as stream:
            content = stream.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise ValueError("input exceeds byte limit")
        return content.decode("utf-8-sig")

    def check_absent(self, paths: tuple[Path, Path]) -> None:
        for path in paths:
            try:
                path.lstat()
            except FileNotFoundError:
                continue
            raise FileExistsError("output already exists")

    def write_pair(
        self, paths: tuple[Path, Path], contents: tuple[bytes, bytes]
    ) -> None:
        created: list[Path] = []
        try:
            with ExitStack() as stack:
                streams = []
                for path in paths:
                    streams.append(stack.enter_context(path.open("xb")))
                    created.append(path)
                for stream, content in zip(streams, contents, strict=True):
                    stream.write(content)
        except OSError:
            cleanup_failed = False
            for path in created:
                try:
                    path.unlink()
                except OSError:
                    cleanup_failed = True
            if cleanup_failed:
                raise OSError(
                    "output cleanup failed; partial files may remain"
                ) from None
            raise
