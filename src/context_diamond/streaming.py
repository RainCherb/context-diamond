"""Incremental streaming capsule updates.

StreamingCompressor avoids full rebuilds when new messages arrive. It keeps
the previous shard state, adds only new shards, and re-renders the capsule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .compressor import CompressionConfig, ContextDiamondCompressor
from .model import ContextCapsule, Message, SentenceShard


@dataclass
class StreamingState:
    """Internal mutable state for a streaming compressor session."""

    messages: list[Message] = field(default_factory=list)
    shards: list[SentenceShard] = field(default_factory=list)
    capsule: ContextCapsule | None = None


class StreamingCompressor:
    """Build capsules incrementally as new messages arrive.

    Usage:
        streamer = StreamingCompressor(CompressionConfig(token_budget=800))
        capsule1 = streamer.add_message("User: Build a login form.")
        capsule2 = streamer.add_message("Assistant: Decision: use JWT tokens.")
    """

    def __init__(self, config: CompressionConfig | None = None) -> None:
        self.config = config or CompressionConfig()
        self._compressor = ContextDiamondCompressor(self.config)
        self._state = StreamingState()

    def add_message(
        self,
        text_or_message: str | Message | dict[str, str],
    ) -> ContextCapsule:
        """Add a message and return the updated capsule.

        *text_or_message* may be plain text, a ``Message`` dataclass, or a dict
        with ``role`` and ``content`` keys.
        """
        if isinstance(text_or_message, str):
            message = Message(role="source", content=text_or_message)
        elif isinstance(text_or_message, Message):
            message = text_or_message
        else:
            content = text_or_message.get("content", "")
            role = text_or_message.get("role", "source")
            name = text_or_message.get("name")
            message = Message(role=role, content=content, name=name)

        self._state.messages.append(message)
        # Rebuild shards from the full message list (shards are lightweight).
        self._state.shards = self._compressor.prepare_shards(self._state.messages)
        self._state.capsule = self._compressor.compress(self._state.messages)
        return self._state.capsule

    def add_messages(
        self,
        messages: list[str | Message | dict[str, str]],
    ) -> ContextCapsule:
        """Add multiple messages and return the updated capsule."""
        for item in messages:
            self.add_message(item)
        return self._state.capsule or self._compressor.compress([])

    def replace_messages(
        self,
        messages: list[str | Message | dict[str, str]],
    ) -> ContextCapsule:
        """Replace the entire message list and rebuild the capsule from scratch.

        Useful when upstream context is pruned or re-ordered.
        """
        self._state = StreamingState()
        return self.add_messages(messages)

    @property
    def current_capsule(self) -> ContextCapsule | None:
        """The most recently produced capsule, or ``None`` if no messages added."""
        return self._state.capsule

    @property
    def message_count(self) -> int:
        """Number of messages accumulated so far."""
        return len(self._state.messages)

    @property
    def shard_count(self) -> int:
        """Number of shards extracted from the current messages."""
        return len(self._state.shards)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the current streaming state (for persistence)."""
        return {
            "messages": [
                {"role": m.role, "content": m.content, "name": m.name}
                for m in self._state.messages
            ],
            "config": {
                "token_budget": self.config.token_budget,
                "title": self.config.title,
                "max_items_per_facet": self.config.max_items_per_facet,
                "include_rehydration_prompt": self.config.include_rehydration_prompt,
                "include_loss_report": self.config.include_loss_report,
                "tokenizer_profile": self.config.tokenizer_profile,
                "facet_weights": dict(self.config.facet_weights),
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StreamingCompressor:
        """Restore a streaming compressor from a serialized state dict."""
        config_data = data.get("config", {})
        config_kwargs: dict[str, Any] = {
            "token_budget": config_data.get("token_budget", 800),
            "title": config_data.get("title", "Context Diamond Capsule"),
            "max_items_per_facet": config_data.get("max_items_per_facet", 6),
            "include_rehydration_prompt": config_data.get("include_rehydration_prompt", True),
            "include_loss_report": config_data.get("include_loss_report", False),
            "tokenizer_profile": config_data.get("tokenizer_profile", "generic"),
        }
        # Restore custom facet weights when present so round-trips preserve
        # template/programmatic tuning instead of silently resetting it.
        facet_weights = config_data.get("facet_weights")
        if isinstance(facet_weights, dict):
            config_kwargs["facet_weights"] = dict(facet_weights)
        config = CompressionConfig(**config_kwargs)
        instance = cls(config)
        raw_messages = data.get("messages", [])
        messages: list[dict[str, str | None]] = []
        for m in raw_messages:
            if isinstance(m, dict):
                messages.append(
                    {
                        "role": m.get("role", "source"),
                        "content": m.get("content", ""),
                        "name": m.get("name"),
                    }
                )
        if messages:
            instance.add_messages(messages)  # type: ignore[arg-type]
        return instance
