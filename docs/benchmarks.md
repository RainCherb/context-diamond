# Benchmarks

Context Diamond includes a deterministic benchmark runner:

```bash
context-diamond-bench examples/chat_transcript.md --budget 420
```

or:

```bash
python -m context_diamond.benchmark examples/chat_transcript.md --budget 420 --format json
```

## What It Measures

The benchmark compares Context Diamond against two simple baselines:

- **Head clipping**: keep the first `N` estimated tokens.
- **Tail clipping**: keep the last `N` estimated tokens.

For each source, it reports:

- estimated source tokens
- estimated capsule tokens
- compression ratio
- signal recall for constraints, decisions, risks, and code/path anchors

Signal recall is a lightweight heuristic. It is not a substitute for task-level
quality evaluation, but it catches a common failure mode: saving tokens while
dropping the exact requirements and decisions that matter.

Short inputs can expand because a capsule includes section headers and metadata.
Use longer handoff corpora for meaningful compression tests:

```bash
context-diamond-bench examples/long_handoff.md --budget 320
```

## Tokenizer Profiles

The runner supports conservative estimate profiles:

```bash
context-diamond-bench examples/chat_transcript.md --profile openai
```

Available profiles:

- `generic`
- `openai`
- `anthropic`
- `gemini`
- `local-bpe`

These profiles are local approximations, not vendor tokenizers. They are useful
for relative comparisons and CI checks without adding heavy dependencies.

## Recommended Project Claim

Do not claim benchmark numbers without publishing the corpus and command used to
produce them. A good release note should include:

```text
Corpus: examples/long_handoff.md
Command: context-diamond-bench examples/long_handoff.md --budget 320
Metric: constraint/decision/risk/code signal recall
```
