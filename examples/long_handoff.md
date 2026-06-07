# Long Agent Handoff

User: Build a public repository for deterministic context compression in LLM
workflows. The project must run locally, must not require API keys, and must
avoid pretending to be a universal replacement for prompt compression.

Assistant: Decision: use structured context capsules with separate sections for
intent, constraints, decisions, facts, current state, open questions, and anchor
entities.

User: The system must preserve hard constraints even when the source transcript
contains noisy logs, repeated status updates, and old implementation details.

Assistant: Current state: the package exposes `context-diamond` and `ctxd` as
CLI commands. The source code lives in `src/context_diamond/`.

Assistant: Decision: add a benchmark runner that compares Context Diamond
against deterministic head and tail clipping baselines.

Assistant: Decision: add dependency-free integration helpers for chat messages,
document-like objects, and tool payloads.

Assistant: Open risk: a deterministic heuristic may miss subtle semantic context
that an LLM-backed compressor could preserve.

Assistant: Open question: should exact tokenizer packages become optional extras
after the public API stabilizes?

Tool: pytest initially failed because `CompressionConfig(token_budget=0)` was not
validated. The fix added config validation and CLI parser validation.

Tool: ruff initially failed because new modules had unsorted imports and lines
over 100 characters. The fix split long lines and ran `python -m ruff check .`.

Noise log 01: the development loop printed environment paths and Windows line
ending warnings.
Noise log 02: repeated status updates mentioned that tests were running.
Noise log 03: repeated status updates mentioned that linting was running.
Noise log 04: repeated status updates mentioned that CLI smoke checks were
running.
Noise log 05: repeated status updates mentioned that docs were being updated.
Noise log 06: repeated status updates mentioned that examples were being added.
Noise log 07: repeated status updates mentioned that benchmark docs were being
added.
Noise log 08: repeated status updates mentioned that integration docs were being
added.
Noise log 09: repeated status updates mentioned that changelog entries were
being updated.
Noise log 10: repeated status updates mentioned that README examples were being
updated.
Noise log 11: repeated status updates mentioned that benchmark output should not
be overclaimed.
Noise log 12: repeated status updates mentioned that short sources may expand
after adding structured section headers.
Noise log 13: repeated status updates mentioned that long sources are better
benchmark inputs.
Noise log 14: repeated status updates mentioned that loss reports help audit
omitted shards.
Noise log 15: repeated status updates mentioned that tokenizer profiles are
approximations.
Noise log 16: repeated status updates mentioned that exact tokenizers can be
optional future dependencies.
Noise log 17: repeated status updates mentioned that public claims need
reproducible commands.
Noise log 18: repeated status updates mentioned that the benchmark corpus should
include constraints and decisions.
Noise log 19: repeated status updates mentioned that comparison baselines should
be simple and deterministic.
Noise log 20: repeated status updates mentioned that the project should remain
zero-dependency by default.

Final requirement: keep the README honest. Do not claim revolutionary status.
Describe the project as auditable context capsules for LLM handoffs.
