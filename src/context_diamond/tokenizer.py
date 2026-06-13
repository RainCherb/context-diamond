"""Small deterministic token estimation utilities.

The estimator intentionally does not imitate any vendor tokenizer exactly. Its
job is to provide stable local budgets before text is sent to an LLM.
"""

from __future__ import annotations

import re

TOKEN_RE = re.compile(
    r"""
    `[^`]+`                         |
    https?://[^\s)]+                |
    [A-Za-z_][A-Za-z0-9_./:-]*      |
    \d+(?:[.,]\d+)?                 |
    [^\w\s]
    """,
    re.VERBOSE,
)

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`\"'])")


def estimate_tokens(text: str) -> int:
    """Return a conservative token estimate for budget planning."""

    if not text.strip():
        return 0

    tokens = TOKEN_RE.findall(text)
    # Long natural-language words and long paths usually split into multiple
    # model tokens. The small surcharge makes budget checks less optimistic.
    surcharge = sum(max(len(token) - 12, 0) // 8 for token in tokens)
    path_bonus = sum(token.count("/") + token.count(".") for token in tokens if "/" in token)
    return len(tokens) + surcharge + path_bonus


def trim_to_token_budget(text: str, budget: int) -> str:
    """Trim text without splitting in the middle of a token-like unit."""

    if budget <= 0:
        return ""

    pieces = TOKEN_RE.findall(text)
    if len(pieces) <= budget:
        return text.strip()

    clipped = " ".join(pieces[:budget]).strip()
    return f"{clipped} ..."


def split_sentences(text: str) -> list[str]:
    """Split text into compact sentence shards while preserving bullet lines."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    shards: list[str] = []

    for kind, block in _markdown_segments(normalized):
        block = block.strip()
        if not block:
            continue
        if kind in {"code", "table"}:
            shards.append(block)
            continue
        block = "\n".join(
            line for line in block.splitlines() if not line.lstrip().startswith("#")
        ).strip()
        if not block:
            continue

        if "\n" in block:
            shards.extend(_split_wrapped_block(block))
        else:
            shards.extend(_split_inline(block))

    return [shard for shard in shards if shard]


def _markdown_segments(text: str) -> list[tuple[str, str]]:
    segments: list[tuple[str, str]] = []
    buffer: list[str] = []
    code_buffer: list[str] = []
    table_buffer: list[str] = []
    in_code = False

    def flush_text() -> None:
        if buffer:
            segments.extend(("text", block) for block in re.split(r"\n{2,}", "\n".join(buffer)))
            buffer.clear()

    def flush_table() -> None:
        if table_buffer:
            segments.append(("table", "\n".join(table_buffer)))
            table_buffer.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            flush_table()
            if in_code:
                code_buffer.append(line)
                segments.append(("code", "\n".join(code_buffer)))
                code_buffer.clear()
                in_code = False
            else:
                flush_text()
                in_code = True
                code_buffer.append(line)
            continue

        if in_code:
            code_buffer.append(line)
            continue

        if _is_table_line(stripped):
            flush_text()
            table_buffer.append(line)
            continue

        flush_table()
        buffer.append(line)

    if in_code and code_buffer:
        segments.append(("code", "\n".join(code_buffer)))
    flush_table()
    flush_text()
    return segments


def _split_inline(text: str) -> list[str]:
    if len(text) < 180:
        return [text.strip()]
    return [part.strip() for part in SENTENCE_RE.split(text) if part.strip()]


def _split_wrapped_block(block: str) -> list[str]:
    shards: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            shards.extend(_split_inline(" ".join(buffer)))
            buffer.clear()

    for line in block.splitlines():
        raw = line.strip()
        if not raw:
            flush()
            continue
        if raw.startswith("#"):
            flush()
            continue

        is_bullet = bool(re.match(r"^[-*]\s+(?:\[[ xX]\]\s+)?", raw))
        is_speaker = bool(re.match(r"^[A-Za-z][A-Za-z _-]{0,24}:\s+", raw))

        if is_bullet:
            flush()
            item = re.sub(r"^[-*]\s+(?:\[[ xX]\]\s+)?", "", raw)
            shards.extend(_split_inline(item))
        elif (is_speaker and buffer) or (buffer and _looks_like_new_sentence_line(buffer[-1], raw)):
            flush()
            buffer.append(raw)
        else:
            buffer.append(raw)

    flush()
    return shards


def _looks_like_new_sentence_line(previous: str, current: str) -> bool:
    return previous.endswith((".", "?", "!")) and current[:1].isupper()


def _is_table_line(line: str) -> bool:
    if not line or "|" not in line:
        return False
    if re.fullmatch(r"\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?", line):
        return True
    return line.count("|") >= 2
