import json
import sys

import pytest

from pepperpaw import cli, courier
from pepperpaw.cli import Failed, answer_line


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Inbox and send log under tmp_path; courier and the to-do command replaced by recorders."""
    monkeypatch.setenv("PEPPERPAW_INBOX", str(tmp_path / "inbox"))
    monkeypatch.setenv("PEPPERPAW_LOG_DIR", str(tmp_path / "board"))
    sent = []

    def send(target, text, source, human=True):
        sent.append({"target": target, "text": text, "source": source, "human": human})
        return {"result": "queued", "detail": f"queued c1 for {target} (w1:p1)", "id": "c1"}

    monkeypatch.setattr(courier, "send", send)
    calls = tmp_path / "todo.jsonl"
    fake = tmp_path / "todo.py"
    fake.write_text(
        "import json, sys\n"
        f"open({str(calls)!r}, 'a', encoding='utf-8').write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "print(sys.argv[2] + ' answered')\n"
        "sys.exit(int(sys.argv[2] == 'Q2'))\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "todo_command", lambda: [sys.executable, "-I", str(fake)])
    return {"sent": sent, "calls": calls, "dir": tmp_path}


def ledger(env):
    path = env["calls"]
    return (
        [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
        if path.exists()
        else []
    )


def log_lines(env):
    path = env["dir"] / "board" / "send-log.jsonl"
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


@pytest.mark.parametrize("q", ["Q1", "q1", "q 1", "ㅂ1", "Ｑ1", "1"])
def test_answer_takes_every_way_of_writing_the_number(q):
    assert answer_line(q, "  keep it ") == ("Q1", "Q1 keep it")


def test_answer_refuses_a_bad_number_or_no_text():
    for q, text in (("Q", "yes"), ("Q1a", "yes"), ("Q1", "  ")):
        with pytest.raises(Failed):
            answer_line(q, text)


def test_send_tags_the_owner_and_the_source_and_logs_no_text(env, capsys):
    assert cli.main(["send", "look at #287"]) == 0
    assert env["sent"] == [
        {
            "target": "secretary",
            "text": "{owner} look at #287 · cli",
            "source": "cli",
            "human": True,
        }
    ]
    (line,) = log_lines(env)
    assert (
        line["who"] == "owner"
        and line["chars"] == len("look at #287")
        and line["result"] == "queued"
    )
    assert "look" not in json.dumps(line)
    assert "secretary: queued" in capsys.readouterr().out


def test_long_text_goes_to_the_inbox_and_is_sent_as_a_path(env, capsys):
    text = "first line\n" + "\n".join(f"line {n}" for n in range(40))
    assert cli.main(["send", text]) == 0
    (saved,) = list((env["dir"] / "inbox").iterdir())
    assert saved.read_text(encoding="utf-8") == text
    (msg,) = env["sent"]
    assert msg["text"].startswith("{owner} first line\n")
    assert f"owner directive file: {saved}" in msg["text"] and msg["text"].endswith(" · cli")
    assert f"saved {saved}" in capsys.readouterr().out


def test_a_file_is_saved_in_the_inbox_and_named_in_the_message(env):
    shot = env["dir"] / "shot.png"
    shot.write_bytes(b"x" * 2048)
    assert cli.main(["send", "see this", "--file", str(shot)]) == 0
    (saved,) = list((env["dir"] / "inbox").iterdir())
    assert saved.name.endswith("-shot.png") and saved.read_bytes() == shot.read_bytes()
    assert env["sent"][0]["text"] == f"{{owner}} see this\nowner file: {saved} (2.0 KB) · cli"


def test_nothing_is_sent_for_an_empty_message_or_a_missing_file(env, capsys):
    assert cli.main(["send", "  "]) == 1
    assert cli.main(["send", "x", "--file", str(env["dir"] / "none.txt")]) == 1
    assert env["sent"] == [] and not (env["dir"] / "inbox").exists()
    err = capsys.readouterr().err
    assert "empty message" in err and "no such file" in err


def test_answer_goes_to_secretary_and_to_the_to_do_list(env, capsys):
    assert cli.main(["answer", "ㅂ1", " keep it "]) == 0
    assert env["sent"][0]["text"] == "{owner} Q1 keep it · cli"
    assert ledger(env) == [["answer", "Q1", "keep it"]]
    assert "to-do list: Q1 answered" in capsys.readouterr().out


def test_a_failed_ledger_write_is_a_failure_after_the_message_is_sent(env, capsys):
    assert cli.main(["answer", "Q2", "no"]) == 1
    assert env["sent"][0]["text"] == "{owner} Q2 no · cli"
    assert "to-do list: Q2 answered" in capsys.readouterr().out


def test_a_refused_send_is_a_failure(env, monkeypatch):
    refused = {"result": "refused", "detail": "courier serve not running (x)", "id": None}
    monkeypatch.setattr(courier, "send", lambda *a, **k: refused)
    assert cli.main(["send", "hi"]) == 1
    assert log_lines(env)[0]["result"] == "refused"


def test_answer_without_a_to_do_command_only_sends(env, monkeypatch, capsys):
    monkeypatch.setattr(cli, "todo_command", lambda: [])
    assert cli.main(["answer", "Q1", "yes"]) == 0
    assert env["sent"][0]["text"] == "{owner} Q1 yes · cli"
    assert not env["calls"].exists() and "to-do list" not in capsys.readouterr().out
