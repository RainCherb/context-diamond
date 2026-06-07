# Context Diamond

> Stop pasting the same messy context into every LLM. Turn chats, logs, issues,
> agent state, and docs into small, auditable context capsules.

[![CI](https://github.com/RainCherb/context-diamond/actions/workflows/ci.yml/badge.svg)](https://github.com/RainCherb/context-diamond/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](pyproject.toml)
[![No API Keys](https://img.shields.io/badge/API%20keys-not%20required-brightgreen.svg)](docs/architecture.md)
[![OpenCode MCP](https://img.shields.io/badge/OpenCode-MCP%20ready-purple.svg)](docs/opencode.md)

Context Diamond is a deterministic context compression toolkit for LLM handoffs.
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

Example benchmark output:

```text
535 source tokens -> 387 rendered capsule tokens
1.38x ratio
constraints:1.00 decisions:1.00 risks:1.00 code:1.00
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
      "timeout": 10000
    }
  }
}
```

OpenCode tools:

- `context_diamond_compress_text`
- `context_diamond_compress_file`
- `context_diamond_benchmark_file`

See [docs/opencode.md](docs/opencode.md).

## CLI

```bash
# Markdown capsule
context-diamond notes.md --budget 500 --output capsule.md

# JSON capsule for automation
context-diamond notes.md --format json --loss-report --output capsule.json

# Stdin
type notes.md | context-diamond - --budget 350
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
- **Structured**: goals, rules, decisions, facts, state, risks, anchors.
- **Composable**: CLI, Python API, JSON output, adapters, MCP.

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
- Optional embedding reranker for very large sources.
- Exact tokenizer extras for OpenAI, Anthropic, Gemini, and local models.
- More first-class agent adapters: GitHub issues, Linear, Slack, Markdown logs.
- Streaming capsule updates for long-running coding agents.
- PyPI release after the public API stabilizes.

## Star This If

- you lose context when switching between LLM tools
- you want OpenCode agents to compress handoffs before continuing
- you prefer inspectable local tools over another black-box summarizer
- you like boring, deterministic software that saves expensive tokens

MIT licensed. Built to be small, honest, and useful.
