# Example Transcript

User: We need a new public project that reduces wasted context tokens when
working with neural networks and LLM agents. The system must be unique enough to
stand alone as an open source repository.

Assistant: Decision: build a deterministic context compressor first, without
requiring API keys. The project can later support optional embeddings or model
plugins.

User: It must create compact context capsules that preserve hard requirements,
current state, decisions, and unresolved questions. Do not make it a generic
one-paragraph summarizer.

Assistant: Current state: the package will expose a Python API and a CLI named
`context-diamond`. The source code should live under `src/context_diamond/`.

User: What about token budgets?

Assistant: Decision: each capsule facet receives a budget share, then the
compressor selects the highest-signal shards inside that budget.

User: Open risk: deterministic heuristics may miss subtle semantics in very
large conversations. Add that to docs and keep optional rerankers on the
roadmap.
