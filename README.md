# Context Diamond v0.7.0

> Stop pasting the same messy context into every LLM. Turn chats, logs, issues,
> agent state, and docs into small, auditable context capsules.

[![CI](https://github.com/RainCherb/context-diamond/actions/workflows/ci.yml/badge.svg)](https://github.com/RainCherb/context-diamond/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](pyproject.toml)
[![No API Keys](https://img.shields.io/badge/API%20keys-not%20required-brightgreen.svg)](docs/architecture.md)
[![OpenCode MCP](https://img.shields.io/badge/OpenCode-MCP%20ready-purple.svg)](docs/opencode.md)

Context Diamond v0.7.0 is a deterministic context compression and handoff toolkit for
LLM agents.
It extracts the things models keep losing in long conversations:

- goals and success criteria
- hard constraints
- decisions already made
- current working state
- open questions and risks
- files, symbols, entities, and anchors

It is built for developers who switch between coding agents, OpenCode, chat UIs,
RAG pipelines, issue threads, and local notes. The default engine is offline,
zero-dependency, inspectable, and safe to run before any text is sent to an LLM.

## Why People Click This

Most LLM context tools promise "memory". Context Diamond gives you a portable
handoff artifact you can read, diff, benchmark, paste, store, or feed to another
agent.

Use it when you want to:

- recover signal from noisy agent sessions
- reduce repeated prompt/context cost
- preserve constraints before handing work to another model
- keep decisions visible instead of buried in a paragraph summary
- audit what got dropped with a loss report
- expose compression as an OpenCode MCP tool

## 60-Second Demo

Install from GitHub:

```bash
pip install git+https://github.com/RainCherb/context-diamond.git
```

Compress a long handoff:

```bash
context-diamond examples/long_handoff.md --budget 320 --title "Sprint Handoff"
```

Get JSON with an audit trail:

```bash
context-diamond examples/long_handoff.md --format json --loss-report
```

Benchmark it against dumb head/tail clipping:

```bash
context-diamond-bench examples/long_handoff.md --budget 320
```

Inspect why shards were selected:

```bash
ctxd explain examples/long_handoff.md
```

Build a capsule from a repository:

```bash
ctxd repo . --budget 1200
```

Compare or merge capsules as the handoff evolves:

```bash
ctxd diff old_capsule.json new_capsule.json
ctxd merge chat.json repo.json issue.json --budget 900
```

Batch-process multiple files:

```bash
ctxd batch notes/*.md --output-dir capsules/ --budget 400 --template coding
```

Use a domain-specific template:

```bash
context-diamond incident_report.md --template incident --budget 500
```

Stream capsules incrementally:

```python
from context_diamond import StreamingCompressor

streamer = StreamingCompressor()
streamer.add_message("Goal: build a login form.")
streamer.add_message("Decision: use JWT tokens.")
capsule = streamer.current_capsule
```

Example benchmark output:

```text
535 source tokens -> 387 rendered capsule tokens
1.38x ratio
constraints:1.00 decisions:1.00 risks:1.00 code:1.00
```

## Direct Token Savings

Context Diamond can automatically adapt compression to your target LLM's context
window, apply multi-level cascade compression, or transparently intercept
messages before they reach an API.

### Adaptive Compression

Compress only when text exceeds the model's usable context:

```bash
context-diamond long_handoff.md --model gpt-4o
```

Recognised models: `gpt-4o`, `gpt-4o-mini`, `claude-3-opus`, `claude-3-sonnet`,
`claude-3-haiku`, `gemini-1.5-pro`, `gemini-1.5-flash`, `llama-3-70b`,
`llama-3-8b`.

```python
from context_diamond import AdaptiveCompressor

adaptive = AdaptiveCompressor()
result = adaptive.compress(long_text, model_name="claude-3-opus")
# result.was_compressed   -> True/False
# result.original_tokens  -> 45000
# result.final_tokens     -> 1800
# result.text             -> capsule markdown or original
```

### Cascade Compression

Multi-level aggressive squeeze (800 -> 400 -> 200 tokens):

```bash
context-diamond very_long_doc.md --cascade --cascade-levels 3
```

```python
from context_diamond import CascadeCompressor

cascade = CascadeCompressor()
capsule = cascade.compress(extremely_long_text)
```

### Middleware (Transparent API Savings)

Auto-compress messages before sending to an LLM:

```python
from context_diamond import AutoCompressMiddleware

middleware = AutoCompressMiddleware(threshold_tokens=1200)
compressed = middleware.compress_messages(messages, model_name="gpt-4o")
# compressed messages have _compressed metadata
print(middleware.savings_report())
# {'tokens_saved': 42000, 'savings_percentage': 87.5}
```

## The Pitch

Generic summaries are cheap, but they often flatten the one thing you needed to
keep. Context Diamond keeps the handoff structured:

| Problem | Context Diamond answer |
| --- | --- |
| "The model forgot the rules." | Rules live in their own section. |
| "We reopened an old decision." | Decisions are extracted separately. |
| "The transcript is mostly noise." | Noise is scored down and shown in loss reports. |
| "I need this in OpenCode." | Run it as a local MCP server. |
| "I do not want another API bill." | No runtime API calls by default. |

## OpenCode MCP

Add Context Diamond to OpenCode as a local MCP server:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "context_diamond": {
      "type": "local",
      "command": ["context-diamond-mcp"],
      "enabled": true,
      "timeout": 30000
    }
  }
}
```

OpenCode tools (prefixed with `context_diamond_`):

- **Compression**: `compress_text`, `compress_file`, `batch_compress`
- **Explainability**: `explain_text`
- **Repository**: `repo_capsule`
- **Benchmark**: `benchmark_file`
- **Streaming**: `streaming_add`, `streaming_get`, `streaming_reset`
- **Discovery**: `list_templates`, `list_tokenizers`, `get_template_info`

See [docs/opencode.md](docs/opencode.md).

## CLI

```bash
# Markdown capsule
context-diamond notes.md --budget 500 --output capsule.md

# JSON capsule for automation
context-diamond notes.md --format json --loss-report --output capsule.json

# Explain shard scoring
ctxd explain notes.md

# Repository capsule
ctxd repo . --budget 1200

# Capsule evolution
ctxd diff old.json new.json
ctxd merge chat.json repo.json --output merged.md

# Stdin
type notes.md | context-diamond - --budget 350

# Precise tokenizers (optional extras)
context-diamond notes.md --tokenizer tiktoken --budget 500
```

Use a JSON message list:

```bash
context-diamond conversation.json --messages-json --format json
```

```json
[
  {"role": "user", "content": "Build a local context compressor."},
  {"role": "assistant", "content": "Decision: use deterministic extraction first."}
]
```

## Python API

```python
from context_diamond import CompressionConfig, ContextDiamondCompressor

text = """
Goal: reduce token waste in LLM handoffs.
The tool must run locally and avoid API keys by default.
Decision: emit markdown and JSON capsules.
"""

compressor = ContextDiamondCompressor(CompressionConfig(token_budget=220))
capsule = compressor.compress(text)

print(capsule.to_markdown())
```

Integration helpers:

```python
from context_diamond import compress_documents, compress_messages, compress_tool_payload
```

See [docs/integrations.md](docs/integrations.md).

## What The Capsule Looks Like

```markdown
# Context Diamond Capsule

- Strategy: `diamond-v1`
- Source tokens: `535`
- Capsule tokens: `315`
- Compression ratio: `1.7x`

## Diamond Pulse
- The strongest signals from the source.

## Rules And Constraints
- Requirements that should not be violated.

## Decisions Already Made
- Choices that should not be reopened accidentally.

## Open Questions And Risks
- Unresolved items that need attention.
```

## Why This Over X

Context Diamond is not trying to replace every prompt compressor, RAG compressor,
or memory store. It is best at one job:

> create auditable context capsules for LLM and coding-agent handoffs.

Read the honest comparison in [docs/why-context-diamond.md](docs/why-context-diamond.md).

## Features

- **Offline by default**: no hidden network calls.
- **Zero runtime dependencies**: install it into boring environments.
- **OpenCode-ready**: ships a local stdio MCP server.
- **Benchmarkable**: compare against deterministic clipping baselines.
- **Auditable**: optional loss report shows omitted shards.
- **Explainable**: `ctxd explain` shows shard facets, scores, tokens, and reasons.
- **Repo-aware**: `ctxd repo` captures branch, git state, and selected files.
- **Composable capsules**: `ctxd diff` and `ctxd merge` support handoff evolution.
- **Structured**: goals, rules, decisions, facts, state, risks, anchors.
- **Composable**: CLI, Python API, JSON output, adapters, MCP.
- **Precise tokenizers**: optional `tiktoken`, `anthropic`, and `transformers` adapters.
- **Templates**: domain-specific presets (`coding`, `support`, `research`, `incident`).
- **Streaming**: `StreamingCompressor` for incremental capsule updates.
- **Batch processing**: `ctxd batch` for multiple files.

## Docs

- [OpenCode integration](docs/opencode.md)
- [Benchmarks](docs/benchmarks.md)
- [Integrations](docs/integrations.md)
- [Algorithm](docs/algorithm.md)
- [Architecture](docs/architecture.md)
- [Use cases](docs/use-cases.md)

## Local Development

```bash
git clone https://github.com/RainCherb/context-diamond.git
cd context-diamond
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

On macOS or Linux, activate with `source .venv/bin/activate`.

## Roadmap

- Larger public benchmark corpus with task-level answer quality checks.
- Domain-adapted embedding reranker profiles.
- More first-class agent adapters: GitHub issues, Linear, Slack, Markdown logs.
- Extended plugin hooks for custom facet detection and scoring.
- PyPI release after the public API stabilizes.

## Star This If

- you lose context when switching between LLM tools
- you want OpenCode agents to compress handoffs before continuing
- you prefer inspectable local tools over another black-box summarizer
- you like boring, deterministic software that saves expensive tokens

MIT licensed. Built to be small, honest, and useful.
