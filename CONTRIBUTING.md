# Contributing

Thanks for improving Context Diamond.

## Local Setup

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

On macOS or Linux, use `source .venv/bin/activate`.

## Guidelines

- Keep the default compressor deterministic and offline.
- Add tests for scoring or budget behavior changes.
- Prefer source-adjacent extraction over hidden abstractive rewrites.
- Document new facets, token budget behavior, or CLI options.

## Commit Style

Use short imperative commit messages, for example:

```text
Add loss report for excluded shards
```
