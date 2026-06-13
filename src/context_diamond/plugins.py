"""Lightweight extension hooks for Context Diamond.

Plugins are deliberately small and dependency-free. They can refine extracted
shards before section selection, while rerankers can reorder shards for optional
semantic or AI-assisted ranking.
"""

from __future__ import annotations

from typing import Protocol

from .model import Message, SentenceShard


class ShardPlugin(Protocol):
    """A plugin that can add, remove, or modify extracted shards."""

    name: str

    def refine_shards(
        self,
        messages: list[Message],
        shards: list[SentenceShard],
    ) -> list[SentenceShard]:
        """Return a refined shard list."""


class ShardReranker(Protocol):
    """A plugin-like object that can reorder shards before capsule selection."""

    name: str

    def rerank(self, shards: list[SentenceShard]) -> list[SentenceShard]:
        """Return shards in preferred order or with updated scores."""


_REGISTERED_PLUGINS: list[ShardPlugin] = []


def register_plugin(plugin: ShardPlugin) -> None:
    """Register a global shard plugin used by new compressor instances."""

    if plugin not in _REGISTERED_PLUGINS:
        _REGISTERED_PLUGINS.append(plugin)


def unregister_plugin(plugin: ShardPlugin) -> None:
    """Remove a registered shard plugin if present."""

    if plugin in _REGISTERED_PLUGINS:
        _REGISTERED_PLUGINS.remove(plugin)


def clear_registered_plugins() -> None:
    """Clear all globally registered shard plugins."""

    _REGISTERED_PLUGINS.clear()


def get_registered_plugins() -> list[ShardPlugin]:
    """Return globally registered plugins in execution order."""

    return list(_REGISTERED_PLUGINS)
