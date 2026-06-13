"""Precise tokenizer adapters for Context Diamond.

Provides optional vendor-specific tokenizers as extras while keeping the
default package zero-dependency.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Re-use the default regex-based estimator for generic fallback
from .tokenizer import estimate_tokens, trim_to_token_budget


class BaseTokenizer(ABC):
    """Abstract base for all tokenizers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tokenizer identifier."""

    @abstractmethod
    def count(self, text: str) -> int:
        """Return the exact or estimated token count for *text*."""

    def truncate(self, text: str, max_tokens: int) -> str:
        """Truncate *text* to fit within *max_tokens*.

        The default implementation uses the conservative regex-based trimmer.
        Subclasses may override this with a more precise truncation when the
        underlying library exposes it.
        """
        return trim_to_token_budget(text, max_tokens)


class GenericTokenizer(BaseTokenizer):
    """Default regex-based conservative estimator."""

    name = "generic"

    def count(self, text: str) -> int:
        return estimate_tokens(text)


class TiktokenTokenizer(BaseTokenizer):
    """OpenAI tiktoken tokenizer (optional extra)."""

    name = "tiktoken"

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        try:
            import tiktoken
        except ImportError as exc:
            msg = (
                "tiktoken is not installed. "
                "Install it with: pip install context-diamond[tiktoken]"
            )
            raise ImportError(msg) from exc
        self._encoding = tiktoken.get_encoding(encoding_name)

    def count(self, text: str) -> int:
        return len(self._encoding.encode(text))

    def truncate(self, text: str, max_tokens: int) -> str:
        tokens: list[int] = self._encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text.strip()
        return str(self._encoding.decode(tokens[:max_tokens])).strip()


class AnthropicTokenizer(BaseTokenizer):
    """Anthropic tokenizer via the ``anthropic`` SDK (optional extra)."""

    name = "anthropic"

    def __init__(self) -> None:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            msg = (
                "anthropic SDK is not installed. "
                "Install it with: pip install context-diamond[anthropic]"
            )
            raise ImportError(msg) from exc
        self._client = Anthropic()

    def count(self, text: str) -> int:
        return int(self._client.count_tokens(text))


class HuggingFaceTokenizer(BaseTokenizer):
    """HuggingFace ``transformers`` tokenizer (optional extra)."""

    name = "transformers"

    def __init__(self, model_name: str = "microsoft/DialoGPT-medium") -> None:
        try:
            from transformers import AutoTokenizer
        except ImportError as exc:
            msg = (
                "transformers is not installed. "
                "Install it with: pip install context-diamond[transformers]"
            )
            raise ImportError(msg) from exc
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model_name = model_name

    def count(self, text: str) -> int:
        return len(self._tokenizer.encode(text, add_special_tokens=False))

    def truncate(self, text: str, max_tokens: int) -> str:
        tokens: list[int] = self._tokenizer.encode(text, add_special_tokens=False)
        if len(tokens) <= max_tokens:
            return text.strip()
        decoded = self._tokenizer.decode(tokens[:max_tokens], skip_special_tokens=True)
        return str(decoded).strip()


#: Registry of built-in tokenizer names → constructor.
TOKENIZER_REGISTRY: dict[str, type[BaseTokenizer]] = {
    "generic": GenericTokenizer,
    "tiktoken": TiktokenTokenizer,
    "anthropic": AnthropicTokenizer,
    "transformers": HuggingFaceTokenizer,
}


def get_tokenizer(name: str, **kwargs: object) -> BaseTokenizer:
    """Return a tokenizer instance by name.

    Raises *ValueError* when *name* is unknown.
    """
    if name not in TOKENIZER_REGISTRY:
        known = ", ".join(sorted(TOKENIZER_REGISTRY))
        msg = f"unknown tokenizer {name!r}; expected one of: {known}"
        raise ValueError(msg)
    return TOKENIZER_REGISTRY[name](**kwargs)


def list_tokenizers() -> list[str]:
    """Return available tokenizer names."""
    return sorted(TOKENIZER_REGISTRY)


def _is_installed(package: str) -> bool:
    """Check whether a Python package is importable."""
    try:
        __import__(package)
        return True
    except ImportError:
        return False


def available_precise_tokenizers() -> list[str]:
    """Return precise tokenizer names whose optional dependencies are satisfied."""
    mapping = {
        "tiktoken": "tiktoken",
        "anthropic": "anthropic",
        "transformers": "transformers",
    }
    return [name for name, pkg in mapping.items() if _is_installed(pkg)]
