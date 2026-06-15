"""Auto-compress middleware for transparent LLM token savings.

Wraps message lists before sending them to an LLM API, compressing any
message content that exceeds a configurable token threshold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .adaptive import AdaptiveCompressor, AdaptiveResult
from .tokenizer import estimate_tokens


@dataclass
class CompressionStats:
    """Running statistics for token savings."""

    tokens_original: int = 0
    tokens_compressed: int = 0
    tokens_saved: int = 0
    compression_count: int = 0
    messages_processed: int = 0
    messages_skipped: int = 0


class AutoCompressMiddleware:
    """Transparently compress long message content before LLM calls.

    Usage:
        middleware = AutoCompressMiddleware(threshold_tokens=1200)
        compressed = middleware.compress_messages(
            [{"role": "user", "content": long_text}], model_name="gpt-4o"
        )
    """

    def __init__(
        self,
        adaptive: AdaptiveCompressor | None = None,
        threshold_tokens: int = 1000,
    ) -> None:
        self.adaptive = adaptive or AdaptiveCompressor()
        self.threshold = threshold_tokens
        self.stats = CompressionStats()

    def _is_already_compressed(self, content: str) -> bool:
        """Heuristic to skip re-compressing a capsule."""
        markers = ("# Context Diamond", "- Strategy: `diamond-v1`", "[CAPSULE]")
        return any(marker in content for marker in markers)

    def _compress_content(self, content: str, model_name: str) -> AdaptiveResult:
        """Compress a single text string."""
        original_tokens = estimate_tokens(content)
        result = self.adaptive.compress(content, model_name)

        self.stats.tokens_original += original_tokens
        self.stats.tokens_compressed += result.final_tokens
        if result.was_compressed:
            self.stats.tokens_saved += original_tokens - result.final_tokens
            self.stats.compression_count += 1

        return result

    def _exceeds_threshold(self, content: str) -> bool:
        """Return ``True`` when *content* uses more tokens than the threshold.

        The threshold is expressed in tokens (as the parameter name promises),
        not in characters. A quick character pre-check avoids the cost of
        tokenising content that is obviously short.
        """

        if len(content) < self.threshold:
            return False
        return estimate_tokens(content) >= self.threshold

    def compress_text(self, text: str, model_name: str = "default") -> str:
        """Compress a single text string if it exceeds the threshold."""
        if not self._exceeds_threshold(text) or self._is_already_compressed(text):
            return text
        result = self._compress_content(text, model_name)
        return result.text

    def compress_messages(
        self,
        messages: list[dict[str, Any]],
        model_name: str = "default",
    ) -> list[dict[str, Any]]:
        """Compress message contents that exceed the threshold.

        Supports plain string ``content`` and OpenAI vision-style lists.
        """
        result: list[dict[str, Any]] = []
        for msg in messages:
            content = msg.get("content")
            if not isinstance(content, str):
                # Vision-style list or other structured content
                if isinstance(content, list):
                    new_content = self._compress_content_list(content, model_name)
                    new_msg = dict(msg)
                    new_msg["content"] = new_content
                    result.append(new_msg)
                else:
                    result.append(msg)
                continue

            self.stats.messages_processed += 1
            if not self._exceeds_threshold(content) or self._is_already_compressed(content):
                self.stats.messages_skipped += 1
                result.append(msg)
                continue

            compressed = self._compress_content(content, model_name)
            new_msg = dict(msg)
            new_msg["content"] = compressed.text
            if compressed.was_compressed:
                new_msg["_compressed"] = True
                new_msg["_original_tokens"] = compressed.original_tokens
                new_msg["_compressed_tokens"] = compressed.final_tokens
            result.append(new_msg)

        return result

    def _compress_content_list(
        self,
        content_list: list[dict[str, Any]],
        model_name: str,
    ) -> list[dict[str, Any]]:
        """Compress text blocks inside a vision-style content list."""
        result: list[dict[str, Any]] = []
        for item in content_list:
            if isinstance(item, dict) and item.get("type") == "text":
                text = str(item.get("text", ""))
                if self._exceeds_threshold(text) and not self._is_already_compressed(text):
                    compressed = self._compress_content(text, model_name)
                    item = dict(item)
                    item["text"] = compressed.text
                    if compressed.was_compressed:
                        item["_compressed"] = True
                result.append(item)
            else:
                result.append(item)
        return result

    def savings_report(self) -> dict[str, Any]:
        """Return a JSON-serializable summary of compression statistics."""
        original = max(self.stats.tokens_original, 1)
        return {
            "tokens_original": self.stats.tokens_original,
            "tokens_compressed": self.stats.tokens_compressed,
            "tokens_saved": self.stats.tokens_saved,
            "compression_count": self.stats.compression_count,
            "messages_processed": self.stats.messages_processed,
            "messages_skipped": self.stats.messages_skipped,
            "savings_percentage": round(
                (self.stats.tokens_saved / original) * 100, 2
            ),
        }

    def reset_stats(self) -> None:
        """Clear accumulated statistics."""
        self.stats = CompressionStats()
