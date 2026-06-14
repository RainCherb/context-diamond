"""Tests for auto-compress middleware."""

from __future__ import annotations

from context_diamond.middleware import AutoCompressMiddleware, CompressionStats


def test_middleware_skips_short_text() -> None:
    middleware = AutoCompressMiddleware(threshold_tokens=100)
    text = "Hello world."
    result = middleware.compress_text(text, model_name="default")
    assert result == text
    assert middleware.stats.compression_count == 0


def test_middleware_skips_already_compressed() -> None:
    middleware = AutoCompressMiddleware(threshold_tokens=100)
    text = "# Context Diamond Capsule\n- Strategy: diamond-v1"
    result = middleware.compress_text(text, model_name="default")
    assert result == text


def test_middleware_compresses_long_text() -> None:
    middleware = AutoCompressMiddleware(threshold_tokens=100)
    text = "Goal: build.\n" + "word " * 10000
    result = middleware.compress_text(text, model_name="llama-3-8b")
    assert "Context Diamond" in result or len(result) < len(text)


def test_middleware_compress_messages_list() -> None:
    middleware = AutoCompressMiddleware(threshold_tokens=100)
    messages = [
        {"role": "user", "content": "Hello."},
        {"role": "user", "content": "Goal: build.\n" + "word " * 10000},
    ]
    result = middleware.compress_messages(messages, model_name="llama-3-8b")
    assert len(result) == 2
    assert result[0]["content"] == "Hello."
    assert result[1].get("_compressed") is True


def test_middleware_skips_compressed_messages() -> None:
    middleware = AutoCompressMiddleware(threshold_tokens=100)
    messages = [
        {"role": "user", "content": "# Context Diamond Capsule\nword " * 500},
    ]
    result = middleware.compress_messages(messages, model_name="llama-3-8b")
    assert result[0]["content"] == messages[0]["content"]


def test_middleware_handles_vision_content() -> None:
    middleware = AutoCompressMiddleware(threshold_tokens=100)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "word " * 500},
                {"type": "image_url", "image_url": {"url": "http://example.com/img.png"}},
            ],
        }
    ]
    result = middleware.compress_messages(messages, model_name="llama-3-8b")
    assert len(result[0]["content"]) == 2
    assert result[0]["content"][0]["type"] == "text"


def test_savings_report() -> None:
    middleware = AutoCompressMiddleware(threshold_tokens=100)
    text = "Goal: build.\n" + "word " * 10000
    middleware.compress_text(text, model_name="llama-3-8b")
    report = middleware.savings_report()
    assert "tokens_original" in report
    assert "tokens_saved" in report
    assert "savings_percentage" in report


def test_reset_stats() -> None:
    middleware = AutoCompressMiddleware(threshold_tokens=100)
    middleware.compress_text("word " * 10000, model_name="llama-3-8b")
    assert middleware.stats.compression_count > 0
    middleware.reset_stats()
    assert middleware.stats.compression_count == 0


def test_compression_stats_dataclass() -> None:
    stats = CompressionStats()
    assert stats.tokens_original == 0
    assert stats.tokens_saved == 0
