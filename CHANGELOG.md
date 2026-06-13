# Changelog

## Unreleased

## 0.7.0 - 2026-06-14

### Core Improvements
- **Precise tokenizer adapters**: `BaseTokenizer` protocol with optional `tiktoken`, `anthropic`, and `transformers` implementations.
- **Template engine**: Domain-specific presets (`coding`, `support`, `research`, `incident`) with tuned facet weights.
- **Streaming capsule updates**: `StreamingCompressor` for incremental context builds without full rebuilds.
- **Batch processing CLI**: `ctxd batch` command for processing multiple files at once.
- **Type safety**: Added `mypy` strict mode and full type coverage.
- **Version bump**: `0.6.3` → `0.7.0`.

### MCP Server Improvements
- **New tools**: `explain_text`, `repo_capsule`, `batch_compress`, `list_templates`, `list_tokenizers`, `get_template_info`.
- **Streaming session management**: `streaming_add`, `streaming_get`, `streaming_reset` for incremental capsule builds over MCP.
- **Template support**: All compression tools support domain-specific templates via the `template` argument.
- **Progress notifications**: `batch_compress` sends progress updates during long-running operations.
- **Enhanced documentation**: Updated `docs/opencode.md` with complete tool reference and examples.

## 0.6.3 - 2026-06-14

- Reworked README and repository positioning for a clearer GitHub landing page.
- Added CLI `--title` support for named capsules.
- Added CLI `--loss-report` and tokenizer profile metadata.
- Clarified budget metadata with `budget_scope` and `profile_rendered_tokens`.
- Added `context-diamond-bench` for deterministic benchmark comparisons.
- Added dependency-free integration helpers for messages, documents, and tool payloads.
- Added a zero-dependency stdio MCP server for OpenCode integration.
- Added `ctxd explain` for shard-level facet, score, token, and reason audits.
- Added `ctxd repo` for repository-state capsules.
- Added `ctxd diff` and `ctxd merge` for JSON capsule evolution.
- Added dependency-free plugin hooks and optional caller-supplied embedding reranking.
- Added markdown/code-aware splitting for fenced code, tables, and task lists.
- Added benchmark recall gates and a strict fixture corpus.
- Added docs for benchmarks, integrations, and "Why Context Diamond".
- Added validation for invalid budgets and malformed message-list input.
- Prevented duplicate capsule items across sections.
- Omitted empty sections from generated capsules.
- Improved markdown heading handling in sentence splitting.

## 0.1.0

- Initial public release.
- Added deterministic diamond-v1 compression.
- Added Markdown and JSON capsule rendering.
- Added CLI commands `context-diamond` and `ctxd`.
- Added examples, docs, and CI.
