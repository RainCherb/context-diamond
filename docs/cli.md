# CLI Reference

```bash
context-diamond INPUT [--budget N] [--format markdown|json] [--output PATH]
```

Alias:

```bash
ctxd INPUT
```

## Arguments

- `INPUT`: source file path or `-` for stdin.
- `--budget`, `-b`: target token budget. Default: `800`.
- `--format`, `-f`: `markdown` or `json`. Default: `markdown`.
- `--output`, `-o`: output path. If omitted, prints to stdout.
- `--messages-json`: parse input as a JSON message list.
- `--no-rehydration-prompt`: omit the final rehydration instructions.

## Examples

```bash
context-diamond examples/chat_transcript.md --budget 500
context-diamond examples/chat_transcript.md --format json --output capsule.json
ctxd - --budget 300 < notes.md
```
