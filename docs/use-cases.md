# Use Cases

## Coding Agents

Compress long agent sessions before handing work to another model. The capsule
preserves requirements, decisions, files, current test state, and blockers.

## Support And Research Threads

Turn long customer or research transcripts into compact context that can be
attached to a follow-up prompt.

## Prompt Cost Control

Use JSON capsules in pipelines that need repeatable context budgets before LLM
calls.

## Evaluation And Regression Checks

Use `context-diamond-bench` in CI to make sure future scoring changes do not
drop constraint, decision, risk, or code/path signals from representative
handoff corpora.

## Knowledge Handoffs

Create short capsules from meeting notes, design docs, incident reviews, or
issue discussions.
