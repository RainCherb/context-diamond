"""Data structures used by the compressor."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

from .tokenizer import estimate_tokens


@dataclass(frozen=True)
class Message:
    """A single conversation message."""

    role: str
    content: str
    name: str | None = None


@dataclass(frozen=True)
class SentenceShard:
    """A scored atomic piece of source context."""

    index: int
    role: str
    text: str
    facet: str
    score: float
    reasons: tuple[str, ...] = ()

    @property
    def tokens(self) -> int:
        return estimate_tokens(self.text)


@dataclass
class CapsuleSection:
    """A named part of a context capsule."""

    title: str
    items: list[str] = field(default_factory=list)

    @property
    def token_count(self) -> int:
        return estimate_tokens(self.title) + sum(estimate_tokens(item) for item in self.items)


@dataclass
class ContextCapsule:
    """Compressed context plus metadata for auditability."""

    title: str
    sections: list[CapsuleSection]
    source_tokens: int
    capsule_tokens: int
    source_sha256: str
    strategy: str = "diamond-v1"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def compression_ratio(self) -> float:
        if self.capsule_tokens == 0:
            return 0.0
        return round(self.source_tokens / self.capsule_tokens, 2)

    @classmethod
    def digest_for(cls, text: str) -> str:
        return sha256(text.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "strategy": self.strategy,
            "source_tokens": self.source_tokens,
            "capsule_tokens": self.capsule_tokens,
            "compression_ratio": self.compression_ratio,
            "source_sha256": self.source_sha256,
            "metadata": self.metadata,
            "sections": [
                {"title": section.title, "items": section.items, "tokens": section.token_count}
                for section in self.sections
            ],
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            "",
            f"- Strategy: `{self.strategy}`",
            f"- Source tokens: `{self.source_tokens}`",
            f"- Capsule tokens: `{self.capsule_tokens}`",
            f"- Compression ratio: `{self.compression_ratio}x`",
            f"- Source SHA-256: `{self.source_sha256[:16]}...`",
            "",
        ]

        for section in self.sections:
            lines.append(f"## {section.title}")
            if section.items:
                lines.extend(f"- {item}" for item in section.items)
            else:
                lines.append("- No high-signal items found.")
            lines.append("")

        return "\n".join(lines).strip() + "\n"
