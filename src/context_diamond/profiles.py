"""Tokenizer profile estimates for planning and benchmarking.

These profiles are conservative approximations, not vendor tokenizers. They are
useful when comparing relative budgets without adding heavy optional
dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass

from .tokenizer import estimate_tokens


@dataclass(frozen=True)
class TokenizerProfile:
    """A named token-estimation profile."""

    name: str
    multiplier: float
    description: str


TOKENIZER_PROFILES = {
    "generic": TokenizerProfile(
        name="generic",
        multiplier=1.0,
        description="Default stable local estimate.",
    ),
    "openai": TokenizerProfile(
        name="openai",
        multiplier=1.08,
        description="Slightly conservative estimate for common OpenAI BPE tokenizers.",
    ),
    "anthropic": TokenizerProfile(
        name="anthropic",
        multiplier=1.06,
        description="Slightly conservative estimate for Claude-style token budgets.",
    ),
    "gemini": TokenizerProfile(
        name="gemini",
        multiplier=1.04,
        description="Slightly conservative estimate for Gemini-style token budgets.",
    ),
    "local-bpe": TokenizerProfile(
        name="local-bpe",
        multiplier=1.12,
        description="Conservative estimate for local BPE/SentencePiece models.",
    ),
}


def list_tokenizer_profiles() -> list[str]:
    """Return available tokenizer profile names."""

    return sorted(TOKENIZER_PROFILES)


def estimate_profile_tokens(text: str, profile: str = "generic") -> int:
    """Estimate tokens with a named profile."""

    if profile not in TOKENIZER_PROFILES:
        known = ", ".join(list_tokenizer_profiles())
        msg = f"unknown tokenizer profile {profile!r}; expected one of: {known}"
        raise ValueError(msg)

    base = estimate_tokens(text)
    if base == 0:
        return 0
    return max(1, round(base * TOKENIZER_PROFILES[profile].multiplier))
