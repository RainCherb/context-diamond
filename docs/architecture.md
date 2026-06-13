# Architecture

Context Diamond is built around a small deterministic pipeline:

```text
source text/messages
  -> sentence shards with facet detection and scoring
  -> plugin refinement
  -> optional reranking
  -> budgeted facet selection
  -> optional loss report
  -> capsule rendering
```

## Modules

- `tokenizer.py` estimates local token budgets and splits source text.
- `extractors.py` assigns each shard to a facet and extracts entities.
- `compressor.py` selects shards and creates a `ContextCapsule`.
- `benchmark.py` compares capsules with deterministic clipping baselines.
- `capsules.py` compares and merges JSON capsules.
- `integrations.py` adapts chat messages, documents, and tool payloads.
- `mcp_server.py` exposes compression and benchmark tools over stdio MCP.
- `plugins.py` defines dependency-free plugin and reranker protocols.
- `profiles.py` provides conservative tokenizer estimate profiles.
- `repo.py` collects repository state and selected files for coding-agent capsules.
- `rerankers.py` contains optional reranking helpers.
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

The current implementation can be extended in several places:

- tokenizer profiles for vendor-specific token counting
- scoring rules for domain-specific importance
- shard plugins registered with `register_plugin()`
- rerankers for optional embedding or LLM-backed selection
- adapters for additional agent runtimes and issue trackers

These additions should preserve the current no-network default.

## Optional Embedding Reranking

`EmbeddingReranker` accepts a caller-provided embedding function:

```python
from context_diamond import CompressionConfig, ContextDiamondCompressor, EmbeddingReranker

def embed(texts: list[str]) -> list[list[float]]:
    return my_embedding_provider(texts)

compressor = ContextDiamondCompressor(
    CompressionConfig(reranker=EmbeddingReranker(embed, query="constraints decisions risks"))
)
```

Context Diamond does not import an embedding SDK or make network calls by
itself. Provider-specific code belongs at the application boundary.
