# pepperpaw

A small command line tool for one person who works with agents: `pepperpaw send` hands a message
to a recipient agent through [herdr-courier](https://github.com/NaNIsaac/herdr-courier), and
`pepperpaw answer` replies to a numbered question and, if you configure one, records the answer in
a to-do list. The alias `ppw` is installed too. It needs `courier serve` running.

## Install

<!-- test -->
```sh
uv tool install git+https://github.com/NaNIsaac/pepperpaw
```

## Usage

```sh
ppw send "look at issue 287"
ppw send "the logs from last night" --file run.log
ppw answer Q12 "keep it"
```

- Every message starts with `{owner}` and ends with `· cli`, so the recipient sees where it was typed.
- Text over 30 lines or 4000 characters, and each attached file (up to 50 MB), is saved in the inbox
  and sent as a path.
- `answer` accepts `Q12`, `q12`, `ㅂ12` (the Korean keyboard layout) and `12`, and sends `Q12 <text>`.

## Configuration

| Variable | Meaning | Default |
| --- | --- | --- |
| `PEPPERPAW_INBOX` | folder for long text and attached files | `~/.pepperpaw/inbox` |
| `PEPPERPAW_LOG_DIR` | folder of `send-log.jsonl`, one line per send with sizes and result, never the text | `%LOCALAPPDATA%\pepperpaw` or `~/pepperpaw` |
| `PEPPERPAW_TODO` | command that records an answer; it is run as `<command> answer Q12 "<text>"` | none: `answer` only sends |

## Development

```sh
uv sync --locked
uv run pytest -q
```

## License

MIT
