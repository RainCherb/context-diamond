"""Adaptive compression for direct LLM token savings.

Automatically selects the optimal token budget based on a target model's
context window and reserves space for the expected output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .compressor import CompressionConfig, ContextDiamondCompressor
from .tokenizer import estimate_tokens


@dataclass(frozen=True)
class ModelContextLimit:
    """Context window and output limit for a known model."""

    name: str
    context_window: int
    max_output_tokens: int = 4096


DEFAULT_MODEL_LIMITS: dict[str, ModelContextLimit] = {
    "gpt-4o": ModelContextLimit("gpt-4o", 128000, 16384),
    "gpt-4o-mini": ModelContextLimit("gpt-4o-mini", 128000, 16384),
    "gpt-4-turbo": ModelContextLimit("gpt-4-turbo", 128000, 4096),
    "claude-3-opus": ModelContextLimit("claude-3-opus", 200000, 4096),
    "claude-3-sonnet": ModelContextLimit("claude-3-sonnet", 200000, 4096),
    "claude-3-haiku": ModelContextLimit("claude-3-haiku", 200000, 4096),
    "gemini-1.5-pro": ModelContextLimit("gemini-1.5-pro", 1000000, 8192),
    "gemini-1.5-flash": ModelContextLimit("gemini-1.5-flash", 1000000, 8192),
    "llama-3-70b": ModelContextLimit("llama-3-70b", 8192, 4096),
    "llama-3-8b": ModelContextLimit("llama-3-8b", 8192, 4096),
    "default": ModelContextLimit("default", 128000, 4096),
}


@dataclass(frozen=True)
class AdaptiveResult:
    """Result of adaptive compression with metadata."""

    text: str
    """Final text to send (original or compressed capsule markdown)."""
    capsule: Any | None
    """``ContextCapsule`` if compression was applied, else ``None``."""
    was_compressed: bool
    """Whether the source was compressed."""
    original_tokens: int
    """Token count of the original source."""
    final_tokens: int
    """Token count of the returned text."""
    model_name: str
    """Target model used for budget calculation."""
    budget: int
    """Token budget that was calculated for the model."""


class AdaptiveCompressor:
    """Compress text only when it exceeds a model's usable context window.

    The usable window is ``context_window - output_tokens - reserve_tokens``.
    If the source fits, it is returned unchanged (identity pass-through).
    """

    def __init__(
        self,
        model_limits: dict[str, ModelContextLimit] | None = None,
        default_reserve_ratio: float = 0.15,
        min_budget: int = 100,
    ) -> None:
        self.limits = model_limits or DEFAULT_MODEL_LIMITS
        self.default_reserve_ratio = default_reserve_ratio
        self.min_budget = min_budget

    def _get_limit(self, model_name: str) -> ModelContextLimit:
        return self.limits.get(model_name, self.limits["default"])

    def get_budget(
        self,
        model_name: str,
        source_tokens: int,
        reserve_tokens: int | None = None,
    ) -> int:
        """Return the token budget for *model_name*.

        *reserve_tokens* defaults to ``context_window * default_reserve_ratio``.
        """
        limit = self._get_limit(model_name)
        if reserve_tokens is None:
            reserve_tokens = int(limit.context_window * self.default_reserve_ratio)
        budget = limit.context_window - reserve_tokens
        return max(self.min_budget, budget)

    def should_compress(
        self,
        text: str,
        model_name: str,
        reserve_tokens: int | None = None,
    ) -> bool:
        """Return ``True`` when *text* exceeds the model's usable budget."""
        source_tokens = estimate_tokens(text)
        budget = self.get_budget(model_name, source_tokens, reserve_tokens)
        return source_tokens > budget

    def compress(
        self,
        text: str,
        model_name: str = "default",
        reserve_tokens: int | None = None,
        **config_kwargs: Any,
    ) -> AdaptiveResult:
        """Compress *text* if it exceeds the budget for *model_name*.

        Returns the original text unchanged when it already fits.
        """
        source_tokens = estimate_tokens(text)
        budget = self.get_budget(model_name, source_tokens, reserve_tokens)

        if source_tokens <= budget:
            return AdaptiveResult(
                text=text,
                capsule=None,
                was_compressed=False,
                original_tokens=source_tokens,
                final_tokens=source_tokens,
                model_name=model_name,
                budget=budget,
            )

        config = CompressionConfig(token_budget=budget, **config_kwargs)
        capsule = ContextDiamondCompressor(config).compress(text)
        compressed_text = capsule.to_markdown()
        final_tokens = estimate_tokens(compressed_text)

        return AdaptiveResult(
            text=compressed_text,
            capsule=capsule,
            was_compressed=True,
            original_tokens=source_tokens,
            final_tokens=final_tokens,
            model_name=model_name,
            budget=budget,
        )


def compress_for_model(
    text: str,
    model_name: str = "default",
    reserve_tokens: int | None = None,
    **config_kwargs: Any,
) -> AdaptiveResult:
    """One-shot adaptive compression."""
    return AdaptiveCompressor().compress(text, model_name, reserve_tokens, **config_kwargs)
