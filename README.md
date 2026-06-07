# Context Diamond

Context Diamond is a deterministic context compression system for LLM workflows.
It turns long chats, issue threads, notes, transcripts, and project logs into a
small "context capsule" that preserves the pieces a model needs most:

- intent and success criteria
- hard rules and constraints
- decisions already made
- stable facts
- current working state
- open questions and risks
- entities, file paths, and anchors

The project is intentionally useful without API keys. The default engine is
extractive, auditable, and budget-aware, so it can run locally before any text is
sent to a model.

## Why This Exists

LLM conversations usually lose money and clarity in the same place: repeated
context. People paste the same requirements, decisions, logs, and partial state
again and again. Generic summarization helps, but it often blurs constraints or
forgets why a decision was made.

Context Diamond uses a different shape. Instead of one paragraph summary, it
builds a structured capsule with separate facets. Each facet has its own token
budget and scoring rules. The result is easier for a model to follow and easier
for a human to audit.

## Install

```bash
pip install context-diamond
```

For local development:

```bash
git clone https://github.com/RainCherb/context-diamond.git
cd context-diamond
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

On macOS or Linux, activate with `source .venv/bin/activate`.

## CLI Usage

Compress a markdown transcript into a capsule:

```bash
context-diamond examples/chat_transcript.md --budget 500 --output capsule.md
```

Write JSON for automation:

```bash
ctxd examples/chat_transcript.md --format json --budget 450 --output capsule.json
```

Read from stdin:

```bash
type notes.md | context-diamond - --budget 350
```

Use a JSON message list:

```bash
context-diamond conversation.json --messages-json --format json
```

The JSON input shape is:

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

## The Diamond Capsule

The compressor splits source context into sentence shards, scores them, assigns a
facet, then selects high-signal shards under a target budget.

Facets:

- **Diamond Pulse**: the three strongest signals across the source.
- **Intent And Success Criteria**: what the user or project is trying to achieve.
- **Rules And Constraints**: requirements that should not be violated.
- **Decisions Already Made**: choices that should not be reopened accidentally.
- **Stable Facts**: reusable background information.
- **Current Working State**: files, errors, tests, paths, and implementation state.
- **Open Questions And Risks**: unresolved items that need attention.
- **Entities And Anchors**: names, files, and code identifiers for grounding.

## Example Output

```markdown
# Context Diamond Capsule

- Strategy: `diamond-v1`
- Source tokens: `719`
- Capsule tokens: `188`
- Compression ratio: `3.82x`

## Diamond Pulse
- [user] Goal: create a public context compression toolkit for LLM workflows.
- [assistant] Decision: use deterministic extraction before optional model plugins.

## Rules And Constraints
- [user] The system must be useful without API keys.
```

## Design Principles

- **Deterministic first**: no hidden network calls and no vendor lock-in.
- **Budget-aware**: every facet receives a token budget.
- **Human-auditable**: extracted shards remain close to source wording.
- **LLM-friendly**: the final capsule includes a rehydration prompt.
- **Composable**: future vector, embedding, or model-backed extractors can plug in.

## Roadmap

- Optional embedding reranker for very large sources.
- Loss reports that show which shards were excluded and why.
- Conversation adapters for Slack, GitHub issues, Linear, and Markdown logs.
- Tokenizer profiles for OpenAI, Anthropic, Gemini, and local models.
- Streaming capsule updates for long-running coding agents.

## Repository Layout

```text
src/context_diamond/      library and CLI
tests/                    unit and CLI tests
docs/                     architecture and algorithm notes
examples/                 sample transcript and API usage
.github/workflows/        CI
```

## License

MIT
