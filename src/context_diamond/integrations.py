"""Small adapter helpers for common LLM workflow objects.

The helpers avoid importing LangChain, LlamaIndex, or MCP packages. They accept
plain dictionaries or duck-typed objects and return normal Context Diamond
capsules.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from .compressor import CompressionConfig, ContextDiamondCompressor
from .model import ContextCapsule, Message


def compress_messages(
    messages: list[dict[str, Any]] | list[Message],
    *,
    token_budget: int = 800,
    title: str = "Conversation Handoff",
) -> ContextCapsule:
    """Compress OpenAI/Anthropic-style message dictionaries."""

    config = CompressionConfig(token_budget=token_budget, title=title)
    return ContextDiamondCompressor(config).compress(messages)


def compress_documents(
    documents: Iterable[Any],
    *,
    token_budget: int = 800,
    title: str = "Document Context Capsule",
) -> ContextCapsule:
    """Compress LangChain/LlamaIndex-style document or node objects."""

    chunks = []
    for index, document in enumerate(documents):
        content = _document_content(document)
        metadata = _document_metadata(document)
        prefix = f"Document {index + 1}"
        if metadata:
            prefix += f" metadata={json.dumps(metadata, ensure_ascii=False, sort_keys=True)}"
        chunks.append(f"{prefix}:\n{content}")

    config = CompressionConfig(token_budget=token_budget, title=title)
    return ContextDiamondCompressor(config).compress("\n\n".join(chunks))


def compress_tool_payload(
    payload: Any,
    *,
    token_budget: int = 800,
    title: str = "Tool Output Capsule",
) -> ContextCapsule:
    """Compress MCP/tool payloads, logs, or JSON-like objects."""

    if isinstance(payload, str):
        source = payload
    else:
        source = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)

    config = CompressionConfig(token_budget=token_budget, title=title)
    return ContextDiamondCompressor(config).compress(source)


def _document_content(document: Any) -> str:
    if isinstance(document, dict):
        for key in ("page_content", "text", "content"):
            if key in document:
                return str(document[key])
    for attr in ("page_content", "text", "content"):
        if hasattr(document, attr):
            return str(getattr(document, attr))
    return str(document)


def _document_metadata(document: Any) -> dict[str, Any]:
    metadata: Any
    if isinstance(document, dict):
        metadata = document.get("metadata", {})
    else:
        metadata = getattr(document, "metadata", {})
    return metadata if isinstance(metadata, dict) else {}
