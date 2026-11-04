"""What the owner hands over to secretary, with the same form whether it came from a terminal or another front end."""

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pepperpaw import courier
from pepperpaw.inbox import Inbox, first_line, human_size, is_long, pointer

# The only agent the owner's messages go to.
SEND_TARGET = "secretary"
# One prefix for every owner input; the source at the end tells secretary where it was typed.
SEND_PREFIX = "{owner} "


def tagged(lines: list[str], source: str) -> str:
    return SEND_PREFIX + "\n".join(lines) + f" · {source}"


class SendLog:
    """One JSON line per send: when, who, sizes and the result, never the text or file names."""

    def __init__(self, state_dir: Path):
        self.path = state_dir / "send-log.jsonl"
        self.lock = threading.Lock()

    def add(
        self,
        who: str,
        chars: int,
        files: list[int],
        result: str,
        item_id: str | None,
        target: str = SEND_TARGET,
    ):
        line = {
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "target": target,
            "who": who,
            "chars": chars,
            "files": len(files),
            "bytes": sum(files),
            "result": result,
            "id": item_id,
        }
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(line) + "\n")


def deliver(
    text: str, saved: list[tuple[Path, int]], box: Inbox, sent: SendLog, who: str, source: str
) -> dict[str, Any]:
    """One message per send, prefixed once: the text (or its first line), then the file lines."""
    files = [f"owner file: {path} ({human_size(size)})" for path, size in saved]
    paths = [str(path) for path, _ in saved]
    if is_long(text):
        stored = box.save_text(text)
        lines = [first_line(text), *files, pointer(stored, text)]
        paths.append(str(stored))
    else:
        lines = [text, *files] if text else files
    outcome = courier.send(SEND_TARGET, tagged(lines, source), source)
    sent.add(who, len(text), [size for _, size in saved], outcome["result"], outcome["id"])
    return {**outcome, "saved": paths}
