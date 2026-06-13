"""Template engine for domain-specific context capsules.

A template defines which facets to include, their relative weights, and
presentation settings. This lets users produce capsules tuned for coding
agents, support threads, research notes, or incident reviews.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DEFAULT_FACET_WEIGHTS: dict[str, float] = {
    "pulse": 0.12,
    "goal": 0.14,
    "constraints": 0.16,
    "decisions": 0.16,
    "facts": 0.11,
    "state": 0.15,
    "open_loops": 0.12,
    "glossary": 0.04,
}


@dataclass(frozen=True)
class CapsuleTemplate:
    """A domain-specific capsule configuration preset.

    Templates override ``CompressionConfig`` defaults so users can select a
    shape without manually tuning every weight.
    """

    name: str
    description: str
    title: str = "Context Diamond Capsule"
    max_items_per_facet: int = 6
    include_rehydration_prompt: bool = True
    facet_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_FACET_WEIGHTS))
    included_facets: tuple[str, ...] = (
        "pulse",
        "goal",
        "constraints",
        "decisions",
        "facts",
        "state",
        "open_loops",
        "glossary",
    )
    custom_sections: tuple[dict[str, Any], ...] = ()

    def to_config_kwargs(self, token_budget: int = 800) -> dict[str, Any]:
        """Return a dict suitable for ``CompressionConfig(**kwargs)``."""
        return {
            "token_budget": token_budget,
            "title": self.title,
            "max_items_per_facet": self.max_items_per_facet,
            "include_rehydration_prompt": self.include_rehydration_prompt,
            "facet_weights": dict(self.facet_weights),
        }


#: Pre-defined templates for common domains.
CODING = CapsuleTemplate(
    name="coding",
    description="Prioritizes code, decisions, constraints, and current state.",
    title="Coding Context Capsule",
    max_items_per_facet=8,
    facet_weights={
        "pulse": 0.10,
        "goal": 0.12,
        "constraints": 0.18,
        "decisions": 0.18,
        "facts": 0.08,
        "state": 0.20,
        "open_loops": 0.10,
        "glossary": 0.04,
    },
    included_facets=(
        "pulse",
        "goal",
        "constraints",
        "decisions",
        "state",
        "open_loops",
        "glossary",
    ),
    custom_sections=(),
)

SUPPORT = CapsuleTemplate(
    name="support",
    description="Prioritizes constraints, open questions, and state for support threads.",
    title="Support Context Capsule",
    max_items_per_facet=7,
    facet_weights={
        "pulse": 0.10,
        "goal": 0.10,
        "constraints": 0.20,
        "decisions": 0.10,
        "facts": 0.10,
        "state": 0.20,
        "open_loops": 0.15,
        "glossary": 0.05,
    },
    included_facets=(
        "pulse",
        "constraints",
        "state",
        "open_loops",
        "decisions",
        "glossary",
    ),
)

RESEARCH = CapsuleTemplate(
    name="research",
    description="Prioritizes facts, decisions, and open questions for research notes.",
    title="Research Context Capsule",
    max_items_per_facet=6,
    facet_weights={
        "pulse": 0.10,
        "goal": 0.10,
        "constraints": 0.10,
        "decisions": 0.15,
        "facts": 0.25,
        "state": 0.10,
        "open_loops": 0.15,
        "glossary": 0.05,
    },
    included_facets=(
        "pulse",
        "goal",
        "decisions",
        "facts",
        "open_loops",
        "glossary",
    ),
)

INCIDENT = CapsuleTemplate(
    name="incident",
    description="Prioritizes state, constraints, and decisions for incident reviews.",
    title="Incident Context Capsule",
    max_items_per_facet=8,
    facet_weights={
        "pulse": 0.12,
        "goal": 0.08,
        "constraints": 0.18,
        "decisions": 0.15,
        "facts": 0.10,
        "state": 0.22,
        "open_loops": 0.12,
        "glossary": 0.03,
    },
    included_facets=(
        "pulse",
        "constraints",
        "decisions",
        "state",
        "open_loops",
        "facts",
        "glossary",
    ),
)

DEFAULT = CapsuleTemplate(
    name="default",
    description="General-purpose balanced template.",
    title="Context Diamond Capsule",
    max_items_per_facet=6,
    facet_weights=dict(DEFAULT_FACET_WEIGHTS),
    included_facets=(
        "pulse",
        "goal",
        "constraints",
        "decisions",
        "facts",
        "state",
        "open_loops",
        "glossary",
    ),
)

_TEMPLATE_REGISTRY: dict[str, CapsuleTemplate] = {
    "default": DEFAULT,
    "coding": CODING,
    "support": SUPPORT,
    "research": RESEARCH,
    "incident": INCIDENT,
}


def list_templates() -> list[str]:
    """Return available template names."""
    return sorted(_TEMPLATE_REGISTRY)


def get_template(name: str) -> CapsuleTemplate:
    """Return a template by name.

    Raises *ValueError* when *name* is unknown.
    """
    if name not in _TEMPLATE_REGISTRY:
        known = ", ".join(list_templates())
        msg = f"unknown template {name!r}; expected one of: {known}"
        raise ValueError(msg)
    return _TEMPLATE_REGISTRY[name]


def register_template(name: str, template: CapsuleTemplate) -> None:
    """Register a custom template."""
    _TEMPLATE_REGISTRY[name] = template
