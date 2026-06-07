# Architecture

Context Diamond is built around a small deterministic pipeline:

```text
source text/messages
  -> sentence shards
  -> facet detection
  -> importance scoring
  -> budgeted facet selection
  -> capsule rendering
```

## Modules

- `tokenizer.py` estimates local token budgets and splits source text.
- `extractors.py` assigns each shard to a facet and extracts entities.
- `compressor.py` selects shards and creates a `ContextCapsule`.
- `model.py` contains dataclasses for messages, shards, sections, and capsules.
- `cli.py` exposes the package as `context-diamond` and `ctxd`.

The default CLI and library path have no runtime dependencies outside the Python
standard library.

## Why Deterministic Extraction

The default compressor is designed to run before any LLM call. That means it
must be predictable, cheap, and inspectable. Instead of asking a model to
summarize, Context Diamond keeps source-adjacent shards and organizes them into
facets that are useful for downstream reasoning.

## Extension Points

The current implementation can be extended in three places:

- tokenizer profiles for vendor-specific token counting
- scoring rules for domain-specific importance
- rerankers for optional embedding or LLM-backed selection

These additions should preserve the current no-network default.
