# Integrations

Context Diamond has small dependency-free adapter helpers in
`context_diamond.integrations`.

## Chat Messages

```python
from context_diamond import compress_messages

capsule = compress_messages(
    [
        {"role": "user", "content": "Goal: reduce token waste."},
        {"role": "assistant", "content": "Decision: use local extraction."},
    ],
    token_budget=500,
)
```

## LangChain Or LlamaIndex-Style Documents

The adapter accepts dictionaries or objects with `page_content`, `text`, or
`content` fields. Metadata is included when available.

```python
from context_diamond import compress_documents

capsule = compress_documents(
    [
        {"page_content": "The system must run offline.", "metadata": {"source": "spec.md"}},
    ],
    token_budget=500,
)
```

## Tool Or MCP Payloads

```python
from context_diamond import compress_tool_payload

capsule = compress_tool_payload(
    {"tool": "pytest", "status": "failed", "error": "test_cli.py must be updated"},
    token_budget=300,
)
```

These helpers intentionally return normal `ContextCapsule` objects, so the same
Markdown and JSON rendering APIs apply everywhere.
