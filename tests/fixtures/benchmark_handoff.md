Goal: ship repository-aware context capsules for coding agents.
The system must keep constraints and must not require network calls.
Decision: add explain, repo, diff, and merge commands.
Current state: implementation lives in `src/context_diamond/cli.py` and `src/context_diamond/repo.py`.
Open question: should embedding reranking remain optional?
Risk: benchmark changes could hide dropped requirements.

Background note 1: users often paste long handoffs into agent chats.
Background note 2: repeated logs can distract from decisions.
Background note 3: summaries are useful but can over-flatten constraints.
