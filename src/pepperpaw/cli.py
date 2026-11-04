"""``pepperpaw send`` and ``pepperpaw answer`` (alias ``ppw``): the owner's messages to secretary.

A message goes through courier serve with the prefix ``{owner}`` and ``· cli`` at the end. Long text
and attached files are saved in the inbox and sent as paths. ``answer`` also records the answer in
a to-do list when PEPPERPAW_TODO names a command for it, so an answer has one path, not one for
the recipient and another for the ledger.
"""

import argparse
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

from pepperpaw.inbox import Inbox
from pepperpaw.outbox import SendLog, deliver

SOURCE = "cli"
WHO = "owner"
UPLOAD_MAX_MB = 50
# "Q1", "q 1", "ㅂ1" (Q typed with the Korean keyboard on) and "1" all name question 1.
QUESTION = re.compile(r"^\s*[QqㅂＱｑ]?\s*(\d+)\s*$")


class Failed(Exception):
    """A refusal to report on stderr; the exit code is 1."""


def inbox_dir() -> Path:
    if found := os.environ.get("PEPPERPAW_INBOX"):
        return Path(found)
    return Path.home() / ".pepperpaw" / "inbox"


def log_dir() -> Path:
    if found := os.environ.get("PEPPERPAW_LOG_DIR"):
        return Path(found)
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "pepperpaw"


def todo_command() -> list[str]:
    return shlex.split(os.environ.get("PEPPERPAW_TODO", ""))


def answer_line(question: str, text: str) -> tuple[str, str]:
    if not (m := QUESTION.match(question)):
        raise Failed(f"not a question number: {question}")
    if not text.strip():
        raise Failed("empty answer")
    return f"Q{m[1]}", f"Q{m[1]} {text.strip()}"


def check_files(files: list[Path]) -> None:
    """Missing or oversized files stop the command before anything is saved or sent."""
    if missing := [str(f) for f in files if not f.is_file()]:
        raise Failed(f"no such file: {', '.join(missing)}")
    limit = UPLOAD_MAX_MB * 1024 * 1024
    if too_big := [f.name for f in files if f.stat().st_size > limit]:
        raise Failed(f"over {UPLOAD_MAX_MB} MB: {', '.join(too_big)}")


def send_message(text: str, files: list[Path]) -> bool:
    text = text.replace("\r\n", "\n").strip()
    if not text and not files:
        raise Failed("empty message")
    check_files(files)
    box = Inbox(inbox_dir())
    saved = []
    for path in files:
        with path.open("rb") as f:
            saved.append(box.save_file(path.name, f))
    outcome = deliver(text, saved, box, SendLog(log_dir()), WHO, SOURCE)
    for path in outcome.get("saved") or []:
        print(f"saved {path}")
    print(f"secretary: {outcome['result']}: {outcome['detail']}")
    return outcome["result"] == "queued"


def record_answer(key: str, text: str) -> bool:
    if not (command := todo_command()):
        return True
    done = subprocess.run(
        [*command, "answer", key, text.strip()],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    out = (done.stdout + done.stderr).strip()
    print(f"to-do list: {out or f'exit {done.returncode}'}")
    return done.returncode == 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pepperpaw", description="The owner's messages to secretary (alias ppw)."
    )
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("send", help="send a message to secretary")
    s.add_argument("text", nargs="?", default="", help="the message; long text is saved as a file")
    s.add_argument("--file", action="append", default=[], type=Path, help="attach a file")
    a = sub.add_parser("answer", help="answer a numbered question: to secretary and the to-do list")
    a.add_argument("question", help="Q1, q1, ㅂ1 or 1")
    a.add_argument("text")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        match args.command:
            case "send":
                return 0 if send_message(args.text, args.file) else 1
            case "answer":
                key, line = answer_line(args.question, args.text)
                sent = send_message(line, [])
                return 0 if record_answer(key, args.text) and sent else 1
    except Failed as exc:
        print(f"pepperpaw {args.command}: {exc}", file=sys.stderr)
        return 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    sys.exit(main())
