# CLI Reference

```bash
context-diamond INPUT [--budget N] [--title TEXT] [--format markdown|json] [--output PATH]
```

Alias:

```bash
ctxd INPUT
```

## Arguments

- `INPUT`: source file path or `-` for stdin.
- `--budget`, `-b`: target token budget. Default: `800`.
- `--title`, `-t`: title used in Markdown and JSON output.
- `--format`, `-f`: `markdown` or `json`. Default: `markdown`.
- `--output`, `-o`: output path. If omitted, prints to stdout.
- `--messages-json`: parse input as a JSON message list.
- `--no-rehydration-prompt`: omit the final rehydration instructions.
- `--loss-report`: include kept/omitted shard audit data in JSON metadata.
- `--tokenizer-profile`: add profile-based token estimates to metadata.

`--budget` controls selected capsule sections. Full Markdown output includes
headers and metadata lines, so benchmark reports may show a larger rendered-token
count than the internal section budget.

## Examples

```bash
context-diamond examples/chat_transcript.md --budget 500
context-diamond examples/chat_transcript.md --title "Sprint Handoff"
context-diamond examples/chat_transcript.md --format json --output capsule.json
context-diamond examples/chat_transcript.md --format json --loss-report
ctxd - --budget 300 < notes.md
```

Invalid budgets, unreadable files, malformed JSON, and invalid message objects
are reported as CLI usage errors.

## Message JSON Shape

```json
[
  {"role": "user", "content": "Build a local context compressor."},
  {"role": "assistant", "content": "Decision: start with deterministic extraction."}
]
```

Each message must be an object. `role` and `content` must be strings. `name` is
optional and must also be a string when provided.
