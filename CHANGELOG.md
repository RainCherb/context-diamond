# Changelog

## Unreleased

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
