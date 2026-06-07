"""Context Diamond compression engine."""

from __future__ import annotations

from dataclasses import dataclass, field

from .extractors import FACET_TITLES, create_shards, extract_entities, normalize_messages
from .model import CapsuleSection, ContextCapsule, Message, SentenceShard
from .tokenizer import estimate_tokens, trim_to_token_budget


@dataclass(frozen=True)
class CompressionConfig:
    """Options controlling capsule shape and size."""

    token_budget: int = 800
    title: str = "Context Diamond Capsule"
    max_items_per_facet: int = 6
    include_rehydration_prompt: bool = True
    facet_weights: dict[str, float] = field(
        default_factory=lambda: {
            "pulse": 0.12,
            "goal": 0.14,
            "constraints": 0.16,
            "decisions": 0.16,
            "facts": 0.15,
            "state": 0.15,
            "open_loops": 0.08,
            "glossary": 0.04,
        }
    )

    def __post_init__(self) -> None:
        if self.token_budget <= 0:
            msg = "token_budget must be greater than zero"
            raise ValueError(msg)
        if self.max_items_per_facet <= 0:
            msg = "max_items_per_facet must be greater than zero"
            raise ValueError(msg)
        if any(weight < 0 for weight in self.facet_weights.values()):
            msg = "facet weights cannot be negative"
            raise ValueError(msg)


class ContextDiamondCompressor:
    """Builds deterministic, budget-aware LLM context capsules."""

    def __init__(self, config: CompressionConfig | None = None) -> None:
        self.config = config or CompressionConfig()

    def compress(
        self,
        text_or_messages: str | list[Message] | list[dict[str, str]],
    ) -> ContextCapsule:
        messages = normalize_messages(text_or_messages)
        source_text = "\n\n".join(message.content for message in messages)
        source_tokens = estimate_tokens(source_text)
        shards = create_shards(messages)

        sections = self._build_sections(shards)
        if self.config.include_rehydration_prompt:
            sections.append(self._rehydration_section())

        capsule = ContextCapsule(
            title=self.config.title,
            sections=sections,
            source_tokens=source_tokens,
            capsule_tokens=sum(section.token_count for section in sections),
            source_sha256=ContextCapsule.digest_for(source_text),
            metadata={
                "source_messages": len(messages),
                "source_shards": len(shards),
                "token_budget": self.config.token_budget,
            },
        )

        return self._fit_capsule(capsule)

    def _build_sections(self, shards: list[SentenceShard]) -> list[CapsuleSection]:
        selected_sections: list[CapsuleSection] = []
        seen_items: set[str] = set()

        pulse = self._pulse_section(shards)
        if pulse.items:
            selected_sections.append(pulse)

        for facet in ("goal", "constraints", "decisions", "facts", "state", "open_loops"):
            section = self._facet_section(shards, facet, excluded_items=seen_items)
            if section.items:
                selected_sections.append(section)
                seen_items.update(_item_key(item) for item in section.items)

        glossary = self._glossary_section(shards)
        if glossary.items:
            selected_sections.append(glossary)

        return selected_sections

    def _pulse_section(self, shards: list[SentenceShard]) -> CapsuleSection:
        top = sorted(shards, key=lambda shard: shard.score, reverse=True)[:3]
        return CapsuleSection(
            title=FACET_TITLES["pulse"],
            items=[self._format_item(shard) for shard in top],
        )

    def _facet_section(
        self,
        shards: list[SentenceShard],
        facet: str,
        *,
        excluded_items: set[str],
    ) -> CapsuleSection:
        budget = self._facet_budget(facet)
        candidates = [shard for shard in shards if shard.facet == facet]
        candidates.sort(key=lambda shard: (shard.score, shard.index), reverse=True)

        items: list[str] = []
        used = 0
        seen: set[str] = set()

        for shard in candidates:
            item = self._format_item(shard)
            key = _item_key(item)
            if key in excluded_items or key in seen:
                continue
            item_tokens = estimate_tokens(item)
            if items and used + item_tokens > budget:
                continue
            seen.add(key)
            items.append(item)
            used += item_tokens
            if len(items) >= self.config.max_items_per_facet:
                break

        return CapsuleSection(title=FACET_TITLES[facet], items=items)

    def _glossary_section(self, shards: list[SentenceShard]) -> CapsuleSection:
        entities = extract_entities(shards)
        return CapsuleSection(
            title=FACET_TITLES["glossary"],
            items=[f"`{entity}`" for entity in entities],
        )

    def _rehydration_section(self) -> CapsuleSection:
        return CapsuleSection(
            title="Rehydration Prompt",
            items=[
                "Use this capsule as the authoritative project context.",
                "Preserve rules and decisions unless newer user input overrides them.",
                "Ask only for missing information that blocks the next concrete action.",
            ],
        )

    def _facet_budget(self, facet: str) -> int:
        weight = self.config.facet_weights.get(facet, 0.1)
        return max(32, int(self.config.token_budget * weight))

    def _format_item(self, shard: SentenceShard) -> str:
        prefix = f"[{shard.role}] " if shard.role and shard.role != "source" else ""
        return f"{prefix}{shard.text.strip()}"

    def _fit_capsule(self, capsule: ContextCapsule) -> ContextCapsule:
        if capsule.capsule_tokens <= self.config.token_budget:
            return capsule

        fitted_sections: list[CapsuleSection] = []
        running_tokens = 0

        for section in capsule.sections:
            title_tokens = estimate_tokens(section.title)
            available = self.config.token_budget - running_tokens - title_tokens
            if available <= 0:
                break

            items: list[str] = []
            for item in section.items:
                item_tokens = estimate_tokens(item)
                if item_tokens <= available:
                    items.append(item)
                    available -= item_tokens
                elif not items and available > 8:
                    trimmed = _strict_trim(item, available)
                    if trimmed:
                        items.append(trimmed)
                    available = 0

            fitted = CapsuleSection(title=section.title, items=items)
            if fitted.items:
                fitted_sections.append(fitted)
                running_tokens += fitted.token_count

        return ContextCapsule(
            title=capsule.title,
            sections=fitted_sections,
            source_tokens=capsule.source_tokens,
            capsule_tokens=sum(section.token_count for section in fitted_sections),
            source_sha256=capsule.source_sha256,
            strategy=capsule.strategy,
            metadata=capsule.metadata | {"fitted_to_budget": True},
        )


def compress_text(text: str, *, token_budget: int = 800) -> ContextCapsule:
    """Convenience function for one-shot compression."""

    return ContextDiamondCompressor(CompressionConfig(token_budget=token_budget)).compress(text)


def _strict_trim(text: str, budget: int) -> str:
    trim_budget = budget
    while trim_budget > 0:
        clipped = trim_to_token_budget(text, trim_budget)
        if estimate_tokens(clipped) <= budget:
            return clipped
        trim_budget -= 1
    return ""


def _item_key(item: str) -> str:
    return " ".join(item.lower().split())
