# Use Cases

## Coding Agents

Compress long agent sessions before handing work to another model. The capsule
preserves requirements, decisions, files, current test state, and blockers.

Use the `coding` template to prioritise code paths and state, or stream messages
incrementally with `StreamingCompressor`:

```python
from context_diamond import StreamingCompressor

streamer = StreamingCompressor()
streamer.add_message("Goal: implement login with JWT.")
streamer.add_message("Decision: store tokens in httpOnly cookies.")
streamer.add_message("Current state: form UI done, backend pending.")
capsule = streamer.current_capsule
```

## Support And Research Threads

Turn long customer or research transcripts into compact context that can be
attached to a follow-up prompt. The `support` template prioritises constraints
and open questions.

```bash
context-diamond support_thread.md --template support --budget 500
```

## Prompt Cost Control

Use JSON capsules in pipelines that need repeatable context budgets before LLM
calls.

## Evaluation And Regression Checks

Use `context-diamond-bench` in CI to make sure future scoring changes do not
drop constraint, decision, risk, or code/path signals from representative
handoff corpora.

## Knowledge Handoffs

Create short capsules from meeting notes, design docs, incident reviews, or
issue discussions. The `incident` template prioritises state and constraints
for post-mortems.

## Batch Documentation Processing

Process a directory of markdown notes or transcripts into individual capsules:

```bash
ctxd batch docs/*.md --output-dir capsules/ --budget 400 --template research
```
