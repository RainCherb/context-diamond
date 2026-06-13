# CLI Reference

```bash
context-diamond INPUT [--budget N] [--title TEXT] [--format markdown|json] [--output PATH]
context-diamond compress INPUT [--budget N]
context-diamond explain INPUT [--format table|json]
context-diamond repo [PATH] [--include README.md src/app.py]
context-diamond diff OLD.json NEW.json
context-diamond merge A.json B.json [--budget N]
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

## Explain

`explain` exposes the shard-level audit trail used by the compressor:

```bash
ctxd explain examples/chat_transcript.md
ctxd explain messages.json --messages-json --format json
```

The table includes shard index, score, facet, token estimate, scoring reasons,
and source text.

## Repo

`repo` builds a capsule from repository state plus selected files:

```bash
ctxd repo . --budget 1200
ctxd repo . --include README.md pyproject.toml src/context_diamond/cli.py
```

It includes branch, `git status --short`, `git diff --stat`, default project
files, and changed or untracked text files. File reads stay inside the requested
repository path.

## Diff And Merge

Diff compares JSON capsules by section item:

```bash
ctxd diff old_capsule.json new_capsule.json
ctxd diff old_capsule.json new_capsule.json --format json
```

Merge deduplicates section items across multiple JSON capsules:

```bash
ctxd merge handoff.json issue.json repo.json --output merged.md
ctxd merge handoff.json issue.json repo.json --budget 900 --format json
```
