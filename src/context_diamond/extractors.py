"""Deterministic feature extraction for Context Diamond."""

from __future__ import annotations

import re
from collections import Counter

from .model import Message, SentenceShard
from .tokenizer import estimate_tokens, split_sentences

FACET_TITLES = {
    "pulse": "Diamond Pulse",
    "goal": "Intent And Success Criteria",
    "constraints": "Rules And Constraints",
    "decisions": "Decisions Already Made",
    "facts": "Stable Facts",
    "state": "Current Working State",
    "open_loops": "Open Questions And Risks",
    "glossary": "Entities And Anchors",
}

FACET_KEYWORDS = {
    "goal": (
        "goal",
        "objective",
        "we need",
        "build",
        "create",
        "ship",
        "deliver",
        "user wants",
        "success",
        "цель",
        "задача",
        "нужно",
        "создай",
        "создать",
        "сделай",
        "реализуй",
        "успех",
    ),
    "constraints": (
        "must",
        "never",
        "do not",
        "cannot",
        "constraint",
        "budget",
        "limit",
        "required",
        "without",
        "avoid",
        "обязательно",
        "нельзя",
        "никогда",
        "не должен",
        "не должно",
        "требование",
        "ограничение",
        "без",
        "избегай",
    ),
    "decisions": (
        "decided",
        "decision",
        "choose",
        "chosen",
        "approved",
        "instead",
        "default",
        "решение",
        "решили",
        "выбрали",
        "выбран",
        "одобрено",
        "по умолчанию",
    ),
    "state": (
        "currently",
        "implemented",
        "failing",
        "failed",
        "failure",
        "error",
        "bug",
        "file",
        "path",
        "branch",
        "test",
        "todo",
        "сейчас",
        "текущий",
        "реализовано",
        "падает",
        "ошибка",
        "баг",
        "файл",
        "путь",
        "ветка",
        "тест",
    ),
    "open_loops": (
        "question",
        "risk",
        "blocked",
        "unknown",
        "unclear",
        "needs",
        "next",
        "follow",
        "investigate",
        "вопрос",
        "риск",
        "заблокировано",
        "неизвестно",
        "неясно",
        "нужно проверить",
        "следующий",
        "исследовать",
    ),
}

CODE_OR_PATH_RE = re.compile(
    r"`[^`]+`|[A-Za-z]:\\[^\s`]+|[A-Za-z0-9_./\\-]+\."
    r"(?:py|ts|tsx|js|jsx|md|json|toml|yml|yaml|txt|log|diff)"
)
ENTITY_RE = re.compile(r"\b[A-Z][A-Za-z0-9]*(?:[A-Z][A-Za-z0-9]*)?\b")


def normalize_messages(
    text_or_messages: object,
) -> list[Message]:
    if isinstance(text_or_messages, str):
        return [Message(role="source", content=text_or_messages)]
    if not isinstance(text_or_messages, list):
        msg = "input must be text or a list of messages"
        raise TypeError(msg)

    messages: list[Message] = []
    for index, item in enumerate(text_or_messages):
        if isinstance(item, Message):
            _validate_message(item, index)
            messages.append(item)
        else:
            if not isinstance(item, dict):
                msg = f"message {index} must be an object with role/content fields"
                raise TypeError(msg)
            content = item.get("content", "")
            role = item.get("role", "source")
            name = item.get("name")
            if not isinstance(content, str):
                msg = f"message {index} content must be a string"
                raise TypeError(msg)
            if not isinstance(role, str):
                msg = f"message {index} role must be a string"
                raise TypeError(msg)
            if name is not None and not isinstance(name, str):
                msg = f"message {index} name must be a string when provided"
                raise TypeError(msg)
            messages.append(
                Message(
                    role=role,
                    content=content,
                    name=name,
                )
            )
    return messages


def _validate_message(message: object, index: int) -> None:
    if not hasattr(message, "role") or not isinstance(getattr(message, "role", None), str):
        msg = f"message {index} role must be a string"
        raise TypeError(msg)
    if not hasattr(message, "content") or not isinstance(getattr(message, "content", None), str):
        msg = f"message {index} content must be a string"
        raise TypeError(msg)
    name = getattr(message, "name", None)
    if name is not None and not isinstance(name, str):
        msg = f"message {index} name must be a string when provided"
        raise TypeError(msg)


def create_shards(messages: list[Message]) -> list[SentenceShard]:
    raw: list[tuple[str, str]] = []
    for message in messages:
        role = message.name or message.role
        for sentence in split_sentences(message.content):
            raw.append((role, sentence))

    total = max(len(raw), 1)
    return [
        SentenceShard(
            index=index,
            role=role,
            text=text,
            facet=detect_facet(text),
            score=score_sentence(text, index=index, total=total, role=role),
            reasons=tuple(score_reasons(text)),
        )
        for index, (role, text) in enumerate(raw)
    ]


def detect_facet(text: str) -> str:
    lowered = f" {text.lower()} "
    compact = text.lower().strip()
    without_speaker = _strip_speaker(compact)

    if compact.startswith("noise log"):
        return "noise"
    if compact.startswith(("```", "~~~", "tool:", "error:", "failure:", "traceback")):
        return "state"
    if without_speaker.startswith(("decision:", "decided:", "choice:", "решение:", "выбрали:")):
        return "decisions"
    if without_speaker.startswith(
        ("current state:", "state:", "currently:", "текущее состояние:", "статус:")
    ):
        return "state"
    if without_speaker.startswith(
        ("open question:", "open risk:", "risk:", "blocked:", "вопрос:", "риск:")
    ):
        return "open_loops"
    if without_speaker.startswith(
        ("final requirement:", "requirement:", "финальное требование:", "требование:")
    ):
        return "constraints"

    if "?" in text:
        return "open_loops"

    hits = {
        facet: sum(1 for keyword in keywords if keyword in lowered)
        for facet, keywords in FACET_KEYWORDS.items()
    }
    facet, count = max(hits.items(), key=lambda item: item[1])
    if count:
        return facet

    if CODE_OR_PATH_RE.search(text):
        return "state"

    return "facts"


def score_sentence(text: str, *, index: int, total: int, role: str) -> float:
    lowered = text.lower()
    score = 1.0

    if role.lower() in {"user", "customer", "owner"} or lowered.startswith("user:"):
        score += 0.45
    if lowered.startswith("noise log"):
        score -= 0.75
    if CODE_OR_PATH_RE.search(text):
        score += 0.4
    if any(
        marker in lowered
        for marker in ("must", "never", "important", "required", "обязательно", "важно", "нельзя")
    ):
        score += 0.55
    if any(
        marker in lowered
        for marker in (
            "must not",
            "do not",
            "cannot",
            "final requirement",
            "не должен",
            "не должно",
        )
    ):
        score += 0.35
    if any(marker in lowered for marker in ("decided", "decision", "will", "chosen", "решение")):
        score += 0.35
    if "?" in text:
        score += 0.3

    token_count = estimate_tokens(text)
    if 8 <= token_count <= 36:
        score += 0.25
    elif token_count > 80:
        score -= 0.25

    recency = index / max(total - 1, 1)
    score += recency * 0.35
    return round(score, 3)


def score_reasons(text: str) -> list[str]:
    lowered = text.lower()
    without_speaker = _strip_speaker(lowered.strip())
    reasons: list[str] = []
    if CODE_OR_PATH_RE.search(text):
        reasons.append("code-or-path")
    if any(
        marker in lowered
        for marker in ("must", "never", "required", "must not", "do not", "обязательно", "нельзя")
    ):
        reasons.append("constraint")
    if any(marker in lowered for marker in ("decided", "decision", "chosen", "решение", "выбрали")):
        reasons.append("decision")
    if "?" in text or without_speaker.startswith(
        ("open question:", "open risk:", "risk:", "blocked:", "вопрос:", "риск:")
    ):
        reasons.append("question")
    return reasons


def extract_entities(shards: list[SentenceShard], *, limit: int = 14) -> list[str]:
    counter: Counter[str] = Counter()
    for shard in shards:
        if shard.facet == "noise":
            continue
        for match in CODE_OR_PATH_RE.findall(shard.text):
            counter[match.strip("`")] += 3
        for match in ENTITY_RE.findall(shard.text):
            if len(match) > 2 and match.lower() not in {"the", "this", "that"}:
                counter[match] += 1

    return [entity for entity, _ in counter.most_common(limit)]


def _strip_speaker(text: str) -> str:
    return re.sub(
        r"^(user|assistant|system|developer|tool|customer|owner):\s+",
        "",
        text,
    )
