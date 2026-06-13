"""Tests for precise tokenizer adapters."""

from __future__ import annotations

import pytest

from context_diamond.tokenizers import (
    TOKENIZER_REGISTRY,
    GenericTokenizer,
    get_tokenizer,
    list_tokenizers,
)


def test_generic_tokenizer_counts() -> None:
    tokenizer = GenericTokenizer()
    assert tokenizer.name == "generic"
    assert tokenizer.count("") == 0
    assert tokenizer.count("hello world") > 0


def test_generic_tokenizer_truncate() -> None:
    tokenizer = GenericTokenizer()
    text = "hello world this is a test"
    assert tokenizer.truncate(text, 100) == text
    truncated = tokenizer.truncate(text, 2)
    assert truncated != text
    assert len(truncated) < len(text)


def test_list_tokenizers() -> None:
    names = list_tokenizers()
    assert "generic" in names
    assert "tiktoken" in names
    assert "anthropic" in names
    assert "transformers" in names


def test_get_tokenizer_generic() -> None:
    tokenizer = get_tokenizer("generic")
    assert tokenizer.name == "generic"


def test_get_tokenizer_unknown() -> None:
    with pytest.raises(ValueError, match="unknown tokenizer"):
        get_tokenizer("nonexistent")


def test_registry_has_all() -> None:
    assert "generic" in TOKENIZER_REGISTRY
    assert "tiktoken" in TOKENIZER_REGISTRY
    assert "anthropic" in TOKENIZER_REGISTRY
    assert "transformers" in TOKENIZER_REGISTRY
