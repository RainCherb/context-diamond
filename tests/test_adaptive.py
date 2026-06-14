"""Tests for adaptive compression and model-aware token budgets."""

from __future__ import annotations

from context_diamond.adaptive import (
    DEFAULT_MODEL_LIMITS,
    AdaptiveCompressor,
    AdaptiveResult,
    ModelContextLimit,
    compress_for_model,
)


def test_model_limits_populated() -> None:
    assert "gpt-4o" in DEFAULT_MODEL_LIMITS
    assert "claude-3-opus" in DEFAULT_MODEL_LIMITS
    assert "gemini-1.5-pro" in DEFAULT_MODEL_LIMITS
    assert "default" in DEFAULT_MODEL_LIMITS


def test_get_budget_for_known_model() -> None:
    adaptive = AdaptiveCompressor()
    budget = adaptive.get_budget("gpt-4o", source_tokens=100000)
    assert budget > 0
    assert budget < 128000


def test_get_budget_for_unknown_model_fallback() -> None:
    adaptive = AdaptiveCompressor()
    budget = adaptive.get_budget("unknown-model", source_tokens=1000)
    assert budget > 0


def test_should_compress_when_over_budget() -> None:
    adaptive = AdaptiveCompressor()
    long_text = "word " * 15000
    assert adaptive.should_compress(long_text, "llama-3-8b")


def test_should_not_compress_when_under_budget() -> None:
    adaptive = AdaptiveCompressor()
    short_text = "Hello world."
    assert not adaptive.should_compress(short_text, "llama-3-8b")


def test_compress_returns_identity_when_fits() -> None:
    adaptive = AdaptiveCompressor()
    text = "Goal: test adaptive."
    result = adaptive.compress(text, model_name="llama-3-8b")
    assert isinstance(result, AdaptiveResult)
    assert not result.was_compressed
    assert result.text == text
    assert result.capsule is None
    assert result.original_tokens == result.final_tokens


def test_compress_returns_capsule_when_over_budget() -> None:
    adaptive = AdaptiveCompressor()
    long_text = "Goal: build a tool.\n" + "word " * 10000
    result = adaptive.compress(long_text, model_name="llama-3-8b")
    assert result.was_compressed
    assert result.capsule is not None
    assert result.final_tokens < result.original_tokens


def test_compress_for_model_convenience() -> None:
    text = "word " * 10000
    result = compress_for_model(text, model_name="llama-3-8b")
    assert isinstance(result, AdaptiveResult)


def test_compress_with_custom_reserve() -> None:
    adaptive = AdaptiveCompressor()
    text = "word " * 10000
    result = adaptive.compress(text, model_name="llama-3-8b", reserve_tokens=5000)
    assert result.was_compressed


def test_compress_min_budget_enforced() -> None:
    adaptive = AdaptiveCompressor(min_budget=500)
    budget = adaptive.get_budget("default", source_tokens=1000000)
    assert budget >= 500


def test_model_context_limit_dataclass() -> None:
    limit = ModelContextLimit("test", 10000, 2048)
    assert limit.context_window == 10000
    assert limit.max_output_tokens == 2048
