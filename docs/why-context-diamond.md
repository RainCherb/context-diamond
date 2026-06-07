# Why Context Diamond

Context Diamond is not trying to be the strongest semantic compressor in the
world. Its niche is narrower: deterministic, auditable context capsules for LLM
handoffs and agent workflows.

## Compared With Naive Summaries

Naive summaries are easy to generate, but they often blur the difference between
facts, decisions, constraints, and unresolved risks. Context Diamond keeps those
signals in separate sections so another model or human can inspect what survived
compression.

Use Context Diamond when:

- constraints must remain visible
- decisions should not be reopened accidentally
- the output needs to be diffable and repeatable
- a local/offline preprocessing step is preferred

## Compared With Prompt Compressors

Model-backed prompt compressors can achieve stronger compression ratios and
better semantic abstraction. They may also add dependencies, latency, cost, and
less inspectable transformations.

Context Diamond is a better fit when you want:

- no runtime API calls
- no mandatory ML model download
- clear sections instead of a dense compressed prompt
- a loss report showing omitted shards

Prompt compressors are a better fit when maximum compression quality matters
more than deterministic auditability.

## Compared With RAG Context Compression

RAG compressors usually compress retrieved documents for a specific query.
Context Diamond focuses on handoffs: chats, project state, tool output, issue
threads, and agent memory.

They can work together: use retrieval to find candidate material, then use
Context Diamond to turn the selected context into a handoff capsule.

## Compared With Memory Stores

Long-term memory systems decide what to remember across sessions. Context
Diamond creates a compact, source-adjacent snapshot for a specific handoff.

Use a memory store for durable recall. Use Context Diamond when you need a
portable capsule that can be pasted into another model, attached to an issue, or
stored as a build artifact.

## Honest Positioning

Context Diamond should be described as:

> Auditable context capsules for LLM handoffs.

It should not be described as:

> A revolutionary universal replacement for prompt compression, RAG, or memory.
