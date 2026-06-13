"""Tests for streaming capsule updates."""

from __future__ import annotations

from context_diamond import CompressionConfig, StreamingCompressor


def test_streaming_empty() -> None:
    streamer = StreamingCompressor()
    assert streamer.current_capsule is None
    assert streamer.message_count == 0
    assert streamer.shard_count == 0


def test_streaming_add_message() -> None:
    streamer = StreamingCompressor(CompressionConfig(token_budget=200))
    capsule = streamer.add_message("Goal: build a context compressor.")
    assert capsule is not None
    assert streamer.message_count == 1
    assert streamer.shard_count > 0
    assert streamer.current_capsule == capsule


def test_streaming_add_messages() -> None:
    streamer = StreamingCompressor(CompressionConfig(token_budget=200))
    capsule = streamer.add_messages(
        [
            "Goal: build a compressor.",
            "Decision: use deterministic extraction.",
        ]
    )
    assert capsule is not None
    assert streamer.message_count == 2


def test_streaming_incremental_growth() -> None:
    streamer = StreamingCompressor(CompressionConfig(token_budget=300))
    c1 = streamer.add_message("Goal: build a tool.")
    c2 = streamer.add_message("Decision: use Python.")
    assert c2.source_tokens >= c1.source_tokens
    assert c2.source_sha256 != c1.source_sha256


def test_streaming_replace_messages() -> None:
    streamer = StreamingCompressor(CompressionConfig(token_budget=200))
    streamer.add_messages(["Goal: build A.", "Decision: use X."])
    capsule = streamer.replace_messages(["Goal: build B."])
    assert capsule is not None
    assert streamer.message_count == 1
    assert "build B" in capsule.to_markdown()


def test_streaming_to_dict_roundtrip() -> None:
    streamer = StreamingCompressor(CompressionConfig(token_budget=200))
    streamer.add_message("Goal: test serialization.")
    data = streamer.to_dict()
    assert data["config"]["token_budget"] == 200
    assert len(data["messages"]) == 1
    assert data["messages"][0]["content"] == "Goal: test serialization."

    restored = StreamingCompressor.from_dict(data)
    assert restored.message_count == 1
    assert restored.current_capsule is not None
    assert "test serialization" in restored.current_capsule.to_markdown()
