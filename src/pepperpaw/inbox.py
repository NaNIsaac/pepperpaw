"""Files the owner hands to secretary: long messages and uploads, saved under one inbox folder.

Nothing here opens or runs what it saves; secretary gets the path and decides what to read.
"""

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

# The operating rule for directives: longer than this goes to secretary as a file and a path.
LONG_LINES = 30
LONG_CHARS = 4000
NAME_CHARS = 120


def is_long(text: str) -> bool:
    return len(text) > LONG_CHARS or text.count("\n") + 1 > LONG_LINES


def safe_name(name: str) -> str:
    """The last path component with only word characters, dots and dashes, never hidden."""
    base = re.split(r"[\\/]", name)[-1]
    clean = re.sub(r"[^\w.\-]+", "_", base).strip("._ ") or "file"
    if len(clean) > NAME_CHARS:
        stem, dot, ext = clean.rpartition(".")
        ext = ext[:16] if dot and stem else ""
        clean = clean[: NAME_CHARS - len(ext) - 1].rstrip("._") + ("." + ext if ext else "")
    return clean


def human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024**2:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1024**2:.1f} MB"


class Inbox:
    def __init__(self, folder: Path, clock=datetime.now):
        self.folder = folder
        self.clock = clock

    def _create(self, name: str) -> tuple[Path, BinaryIO]:
        """A new file named ``<stamp>-<name>``; a clash in the same second gets ``-2``, ``-3``."""
        self.folder.mkdir(parents=True, exist_ok=True)
        first = Path(f"{self.clock():%Y%m%d-%H%M%S}-{name}")
        for n in range(1, 1000):
            path = self.folder / (first if n == 1 else f"{first.stem}-{n}{first.suffix}")
            try:
                return path, path.open("xb")
            except FileExistsError:
                continue
        raise FileExistsError(f"No free name for {first} in {self.folder}")

    def save_text(self, text: str, name: str = "owner.md") -> Path:
        path, f = self._create(name)
        with f:
            f.write(text.encode("utf-8"))
        return path

    def save_file(self, name: str, source: BinaryIO) -> tuple[Path, int]:
        path, f = self._create(safe_name(name))
        with f:
            shutil.copyfileobj(source, f, 1024 * 1024)
            return path, f.tell()


def first_line(text: str) -> str:
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return first[:79] + "…" if len(first) > 80 else first


def pointer(path: Path, text: str) -> str:
    return f"owner directive file: {path} (first line: {first_line(text)})"
