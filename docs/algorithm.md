# Diamond V1 Algorithm

Diamond V1 is an extractive context compression algorithm for LLM handoffs.

## 1. Normalize

Input may be plain text or a list of chat messages. Messages keep their `role`
field so the final capsule can preserve speaker context.

## 2. Shard

The source is split into compact sentence shards. Bullet lists are preserved
because they often contain decisions, tasks, or constraints.

## 3. Classify Facets

Each shard is assigned to one primary facet:

- goal
- constraints
- decisions
- facts
- state
- open loops

Classification is keyword and structure based. Questions become open loops.
Code paths and filenames bias toward current working state.

## 4. Score

Each shard receives an importance score. Signals include:

- user-authored text
- constraints such as "must", "never", and "required"
- decision terms such as "decided" and "chosen"
- code paths and filenames
- questions
- compact sentence length
- recency

## 5. Select Under Budget

Each facet receives a share of the target token budget. The compressor sorts
candidate shards by score and keeps the highest-signal non-duplicate items that
fit in the facet budget.

## 6. Render

The capsule can be rendered as Markdown for direct model prompting or JSON for
automation pipelines.

## Known Tradeoffs

Diamond V1 favors precision over abstraction. It keeps source wording close to
the original, which makes it auditable, but it may be less compact than an
LLM-generated abstract summary. Future versions can add optional abstractive
layers while keeping deterministic extraction as the baseline.
