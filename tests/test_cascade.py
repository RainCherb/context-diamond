"""Tests for multi-level cascade compression."""

from __future__ import annotations

from context_diamond.cascade import DEFAULT_CASCADE_LEVELS, CascadeCompressor, CascadeLevel


def test_default_cascade_has_three_levels() -> None:
    assert len(DEFAULT_CASCADE_LEVELS) == 3
    assert DEFAULT_CASCADE_LEVELS[0].token_budget == 800
    assert DEFAULT_CASCADE_LEVELS[1].token_budget == 400
    assert DEFAULT_CASCADE_LEVELS[2].token_budget == 200


def test_cascade_compresses_text() -> None:
    text = "Goal: build a tool.\n" + "word " * 3000
    compressor = CascadeCompressor()
    capsule = compressor.compress(text)
    assert hasattr(capsule, "to_markdown")
    assert capsule.capsule_tokens < capsule.source_tokens


def test_cascade_early_exit_when_fits() -> None:
    short_text = "Goal: test. Decision: use Python."
    compressor = CascadeCompressor()
    capsule = compressor.compress(short_text)
    assert capsule.source_tokens <= 800


def test_custom_cascade_levels() -> None:
    levels = [
        CascadeLevel(token_budget=100),
        CascadeLevel(token_budget=50, include_rehydration_prompt=False),
    ]
    compressor = CascadeCompressor(levels=levels)
    text = "word " * 500
    capsule = compressor.compress(text)
    assert capsule.capsule_tokens <= 100


def test_cascade_with_template() -> None:
    levels = [
        CascadeLevel(token_budget=400, template="coding"),
    ]
    compressor = CascadeCompressor(levels=levels)
    text = "Goal: build.\nDecision: use Python.\n" + "word " * 1000
    capsule = compressor.compress(text)
    assert capsule.capsule_tokens <= 400


def test_cascade_level_without_rehydration() -> None:
    level = CascadeLevel(token_budget=200, include_rehydration_prompt=False)
    assert not level.include_rehydration_prompt
