"""Optional rerankers for Context Diamond.

The built-in rerankers do not import embedding or LLM SDKs. Instead, callers can
provide embedding functions from OpenAI, local models, or any other provider.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import replace

from .model import SentenceShard

EmbeddingFunction = Callable[[list[str]], Sequence[Sequence[float]]]


class EmbeddingReranker:
    """Rerank shards using caller-supplied embeddings and a query.

    This keeps the default package offline and zero-dependency while still
    supporting optional AI/embedding-assisted selection.
    """

    name = "embedding"

    def __init__(
        self,
        embed: EmbeddingFunction,
        *,
        query: str = "important goals constraints decisions state risks code files",
        semantic_weight: float = 0.35,
    ) -> None:
        if semantic_weight < 0:
            msg = "semantic_weight cannot be negative"
            raise ValueError(msg)
        self.embed = embed
        self.query = query
        self.semantic_weight = semantic_weight

    def rerank(self, shards: list[SentenceShard]) -> list[SentenceShard]:
        if not shards:
            return []

        vectors = list(self.embed([self.query, *[shard.text for shard in shards]]))
        if len(vectors) != len(shards) + 1:
            msg = "embedding function must return one vector per input text"
            raise ValueError(msg)

        query_vector = vectors[0]
        scored: list[SentenceShard] = []
        for shard, vector in zip(shards, vectors[1:], strict=True):
            semantic_score = _cosine(query_vector, vector)
            scored.append(
                replace(
                    shard,
                    score=round(shard.score + semantic_score * self.semantic_weight, 3),
                    reasons=tuple(dict.fromkeys((*shard.reasons, "embedding-rerank"))),
                )
            )

        return sorted(scored, key=lambda shard: (shard.score, shard.index), reverse=True)


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        msg = "embedding vectors must have the same dimensions"
        raise ValueError(msg)

    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
