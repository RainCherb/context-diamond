"""Multi-level cascade compression for extreme token savings.

Applies Context Diamond repeatedly with progressively stricter budgets and
facet weights, stopping early if the result already fits the next level.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .compressor import CompressionConfig, ContextDiamondCompressor
from .model import ContextCapsule
from .tokenizer import estimate_tokens


@dataclass
class CascadeLevel:
    """Configuration for one cascade compression step."""

    token_budget: int
    facet_weights: dict[str, float] | None = None
    max_items_per_facet: int | None = None
    include_rehydration_prompt: bool = True
    template: str | None = None


#: Default 3-level cascade: normal → aggressive → ultra.
DEFAULT_CASCADE_LEVELS = [
    CascadeLevel(
        token_budget=800,
        include_rehydration_prompt=True,
    ),
    CascadeLevel(
        token_budget=400,
        facet_weights={
            "pulse": 0.10,
            "goal": 0.10,
            "constraints": 0.35,
            "decisions": 0.30,
            "facts": 0.05,
            "state": 0.10,
            "open_loops": 0.00,
            "glossary": 0.00,
        },
        max_items_per_facet=4,
        include_rehydration_prompt=False,
    ),
    CascadeLevel(
        token_budget=200,
        facet_weights={
            "pulse": 0.00,
            "goal": 0.00,
            "constraints": 0.50,
            "decisions": 0.40,
            "facts": 0.00,
            "state": 0.10,
            "open_loops": 0.00,
            "glossary": 0.00,
        },
        max_items_per_facet=2,
        include_rehydration_prompt=False,
    ),
]


class CascadeCompressor:
    """Compress text through multiple increasingly strict levels.

    Each level feeds the previous capsule's Markdown output into the next
    compressor. Levels can be omitted early when the current result already
    fits the next budget.
    """

    def __init__(self, levels: list[CascadeLevel] | None = None) -> None:
        self.levels = levels or list(DEFAULT_CASCADE_LEVELS)

    def _build_config(self, level: CascadeLevel) -> CompressionConfig:
        kwargs: dict[str, Any] = {
            "token_budget": level.token_budget,
            "include_rehydration_prompt": level.include_rehydration_prompt,
        }
        if level.max_items_per_facet is not None:
            kwargs["max_items_per_facet"] = level.max_items_per_facet
        if level.facet_weights is not None:
            kwargs["facet_weights"] = dict(level.facet_weights)
        if level.template is not None:
            from .templates import get_template

            template = get_template(level.template)
            template_kwargs = template.to_config_kwargs(token_budget=level.token_budget)
            template_kwargs.update(kwargs)
            kwargs = template_kwargs
            # Re-apply explicit overrides after template
            if level.facet_weights is not None:
                kwargs["facet_weights"] = dict(level.facet_weights)
            if level.max_items_per_facet is not None:
                kwargs["max_items_per_facet"] = level.max_items_per_facet
            kwargs["include_rehydration_prompt"] = level.include_rehydration_prompt
        return CompressionConfig(**kwargs)

    def compress(self, text: str) -> ContextCapsule:
        """Run the cascade and return the final capsule."""
        result_text = text
        for level in self.levels:
            current_tokens = estimate_tokens(result_text)
            # Early exit if already fits
            if current_tokens <= level.token_budget:
                if hasattr(result_text, "to_markdown"):
                    return result_text  # type: ignore[return-value]
                config = self._build_config(level)
                return ContextDiamondCompressor(config).compress(result_text)

            config = self._build_config(level)
            capsule = ContextDiamondCompressor(config).compress(result_text)
            result_text = capsule.to_markdown()

        # If the loop finishes without early return, the last capsule is the result
        if hasattr(result_text, "to_markdown"):
            return result_text  # type: ignore[return-value]
        config = self._build_config(self.levels[-1])
        return ContextDiamondCompressor(config).compress(result_text)
